import asyncio
import json
import socketserver
import struct
import sys
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from simlink.core import Bridge, Config, Minecraft, Rcon, SimlinkError
from simlink.dashboard import make_server


@pytest.fixture
def fake_rcon():
    received = []
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                while True:
                    rid, kind, body = Rcon.receive(self.request)
                    text = body.decode()
                    if kind == 3:
                        self.request.sendall(Rcon.packet(rid if text == 'test-password' else -1, 2, ''))
                        continue
                    received.append(text)
                    answer = {'list':'There are 1 of a max of 20 players online: Alex', 'time query daytime':'The time is 1000', 'time set day':'Set the time to 1000'}.get(text, 'OK')
                    # Two framed replies and intentionally fragmented TCP writes.
                    middle = len(answer)//2
                    data = Rcon.packet(rid, 0, answer[:middle]) + Rcon.packet(rid, 0, answer[middle:])
                    for offset in range(0, len(data), 3):
                        self.request.sendall(data[offset:offset+3])
            except (SimlinkError, OSError):
                pass
    server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1], received
    server.shutdown()
    server.server_close()


@pytest.fixture
def config(tmp_path, fake_rcon):
    return Config('127.0.0.1', fake_rcon[0], 'test-password', tmp_path)


def test_fragmented_real_tcp_read_and_auth(config, fake_rcon):
    observed = Minecraft(config).observe()
    assert 'Alex' in observed['players']
    assert observed['time'] == 'The time is 1000'
    bad = Config('127.0.0.1', config.port, 'wrong', config.state_dir)
    with pytest.raises(SimlinkError, match='Authentification'):
        Minecraft(bad).observe()
    assert 'test-password' not in fake_rcon[1]


@pytest.mark.parametrize('action,args', [
    ('raw', {'command':'stop'}), ('set_time', {'value':'day\nstop'}),
    ('teleport', {'player':'@a','x':0,'y':64,'z':0}),
    ('teleport', {'player':'Alex','x':True,'y':64,'z':0}),
    ('teleport', {'player':'Alex','x':0,'y':1000,'z':0}),
    ('set_weather', {'value':'clear','extra':'stop'})])
def test_reject_commands(config, action, args):
    with pytest.raises(SimlinkError):
        Minecraft(config).command_for(action,args)


def test_approval_once_and_refusal(config, fake_rcon):
    bridge = Bridge(config)
    pending = bridge.propose('set_time', {'value':'day'}, 'Test de jour')
    assert fake_rcon[1] == []
    result = bridge.decide(pending['id'], True)
    assert result['status'] == 'response_received'
    assert result['result'] == 'Set the time to 1000'
    assert fake_rcon[1].count('time set day') == 1
    with pytest.raises(SimlinkError):
        bridge.decide(pending['id'], True)
    other = bridge.propose('set_weather', {'value':'rain'}, 'Test')
    assert bridge.decide(other['id'], False)['status'] == 'rejected'
    assert 'weather rain' not in fake_rcon[1]


def test_expiration_stop_and_shared_state(config, fake_rcon):
    bridge = Bridge(config)
    second = Bridge(config)
    pending = bridge.propose('set_time', {'value':'day'}, 'Test')
    with bridge.db() as db:
        db.execute('UPDATE actions SET expires=0 WHERE id=?', (pending['id'],))
    assert second.decide(pending['id'], True)['status'] == 'expired'
    pending = bridge.propose('set_time', {'value':'night'}, 'Test')
    second.stop()
    assert bridge.action(pending['id'])['status'] == 'cancelled'
    with pytest.raises(SimlinkError, match='suspendues'):
        bridge.propose('set_time', {'value':'day'}, 'Test')
    assert not fake_rcon[1]
    second.stop(False)
    assert bridge.propose('set_time', {'value':'day'}, 'Test')['status'] == 'pending'


def test_concurrent_approval_cannot_execute_twice(config, fake_rcon):
    bridge=Bridge(config)
    item=bridge.propose('set_time', {'value':'day'}, 'Test')
    outcomes=[]
    def approve():
        try: outcomes.append(Bridge(config).decide(item['id'], True)['status'])
        except SimlinkError: outcomes.append('rejected')
    threads=[threading.Thread(target=approve) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(outcomes)==['rejected','response_received']
    assert fake_rcon[1].count('time set day')==1


def test_unknown_not_retried(config):
    class Failing(Minecraft):
        calls=0
        def execute(self, command):
            self.calls+=1
            raise SimlinkError('Réponse non confirmée')
    adapter=Failing(config)
    bridge=Bridge(config,adapter)
    item=bridge.propose('set_time', {'value':'day'}, 'Test')
    assert bridge.decide(item['id'],True)['status']=='unknown'
    with pytest.raises(SimlinkError): bridge.decide(item['id'],True)
    assert adapter.calls==1


def test_loopback_only(tmp_path):
    with pytest.raises(SimlinkError): Config('example.com',25575,'secret',tmp_path)


def test_http_token_origin_and_live_read(config, fake_rcon):
    server, token = make_server(Bridge(config),0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    def request(path, data=None, auth=True, origin=None, host=None):
        headers={'Authorization':'Bearer '+token} if auth else {}
        if origin: headers['Origin']=origin
        if host: headers['Host']=host
        if data is not None: headers['Content-Type']='application/json'
        req=Request(base+path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        with urlopen(req,timeout=10) as response: return json.load(response)
    try:
        for kwargs,code in [({'auth':False},401),({'origin':'https://attacker.example'},403),({'host':'attacker.example'},403)]:
            with pytest.raises(HTTPError) as caught: request('/api/state',**kwargs)
            assert caught.value.code==code
        assert 'Alex' in request('/api/observe')['players']
        item=request('/api/propose', {'action':'set_weather','arguments':{'value':'clear'},'reason':'Test local'})
        assert 'weather clear' not in fake_rcon[1]
        assert request('/api/decide', {'id':item['id'],'approve':True})['status']=='response_received'
        assert fake_rcon[1].count('weather clear')==1
    finally:
        server.shutdown();server.server_close()


def test_mcp_official_client_process(config, tmp_path, fake_rcon):
    path=tmp_path/'test-config.json'
    path.write_text(json.dumps({'host':config.host,'port':config.port,'password':config.password}))
    async def scenario():
        params=StdioServerParameters(command=sys.executable,args=['-m','simlink','--config',str(path),'mcp'])
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                result=await client.list_tools()
                assert {tool.name for tool in result.tools}=={'minecraft_observe','minecraft_player','minecraft_propose','simlink_action_status'}
                observation=await client.call_tool('minecraft_observe',{})
                assert not observation.isError and 'Alex' in str(observation.content)
                proposal=await client.call_tool('minecraft_propose', {'action':'set_time','arguments':{'value':'day'},'reason':'Test MCP'})
                assert not proposal.isError and 'pending' in str(proposal.content)
                assert 'time set day' not in fake_rcon[1]
                pending=Bridge(config).actions()[0]
                Bridge(config).decide(pending['id'],True)
                status=await client.call_tool('simlink_action_status',{'action_id':pending['id']})
                assert 'response_received' in str(status.content)
                invalid=await client.call_tool('minecraft_propose', {'action':'set_time','arguments':{'value':'day\nstop'},'reason':'Invalid'})
                assert invalid.isError
                assert 'stop' not in fake_rcon[1]
                assert len((await client.list_prompts()).prompts)==1
                assert len((await client.list_resources()).resources)==1
    asyncio.run(scenario())


def test_changed_target_cannot_approve_old_request(config):
    bridge=Bridge(config)
    pending=bridge.propose('set_time',{'value':'day'},'Test')
    other=Bridge(Config(config.host,config.port,'different-password',config.state_dir))
    assert other.actions()==[]
    with pytest.raises(SimlinkError): other.decide(pending['id'],True)


def test_tcp_disconnect_after_write_is_unknown(config):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            rid,kind,body=Rcon.receive(self.request)
            self.request.sendall(Rcon.packet(rid,2,''))
            Rcon.receive(self.request)
            # Command received, connection dropped before reply.
    server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler)
    server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        bridge=Bridge(Config('127.0.0.1',server.server_address[1],config.password,config.state_dir))
        item=bridge.propose('set_time',{'value':'day'},'Test interruption')
        result=bridge.decide(item['id'],True)
        assert result['status']=='unknown'
        assert 'pu être exécutée' in result['result']
    finally:
        server.shutdown();server.server_close()
