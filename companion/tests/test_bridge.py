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
from simlink.core import Bridge, Config, Factorio, Kerbal, Minecraft, Rcon, SimlinkError
from simlink.dashboard import make_server


@pytest.fixture
def fake_rcon():
    received = []
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                while True:
                    rid, kind, body = Rcon.receive(self.request)
                    # Vanilla Minecraft drops the client when two requests share one segment.
                    self.request.settimeout(0.05)
                    try:
                        if self.request.recv(1, socketserver.socket.MSG_PEEK):
                            return
                    except OSError:
                        pass
                    self.request.settimeout(None)
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
    path.write_text(json.dumps({'game':'minecraft','host':config.host,'port':config.port,'password':config.password}))
    async def scenario():
        params=StdioServerParameters(command=sys.executable,args=['-m','simlink','--config',str(path),'mcp'])
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                result=await client.list_tools()
                assert {tool.name for tool in result.tools}=={'minecraft_observe','minecraft_player','minecraft_propose','simlink_action_status'}
                assert (await client.read_resource('simlink://capabilities'))
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


def test_legacy_config_without_game_is_minecraft(tmp_path):
    path=tmp_path/'config.json'
    path.write_text(json.dumps({'host':'127.0.0.1','port':25575,'password':'x'}))
    assert Config.load(path).game=='minecraft'
    with pytest.raises(SimlinkError): Config('127.0.0.1',1,'x',tmp_path,'doom')


@pytest.fixture
def fake_factorio():
    received=[]
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                while True:
                    rid,kind,body=Rcon.receive(self.request); text=body.decode()
                    if kind==3:
                        self.request.sendall(Rcon.packet(rid if text=='test-password' else -1,2,'')); continue
                    received.append(text)
                    if text.startswith('/silent-command rcon.print(helpers.table_to_json({tick'): answer='{"tick":5371,"players":1,"daytime":0.3,"paused":false,"evolution":0.0003,"speed":1}\n'
                    elif text=='/players online': answer='Online players (1):\n  engineer (online)\n'
                    elif text=='/time': answer='1 minute and 29 seconds\n'
                    elif text=='/version': answer='2.1.24\n'
                    elif "get_player('engineer')" in text: answer='{"name":"engineer","online":true,"surface":"nauvis","position":{"x":1.5,"y":-2},"health":250}\n'
                    else: answer=''
                    self.request.sendall(Rcon.packet(rid,0,answer))
            except (SimlinkError,OSError): pass
    server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler); server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    yield server.server_address[1],received
    server.shutdown(); server.server_close()


def test_factorio_adapter(tmp_path, fake_factorio):
    config=Config('127.0.0.1',fake_factorio[0],'test-password',tmp_path,'factorio')
    bridge=Bridge(config)
    assert isinstance(bridge.adapter,Factorio)
    observed=bridge.adapter.observe()
    assert observed['state']['tick']==5371 and 'engineer' in observed['players']
    assert bridge.adapter.player('engineer')['data']['health']==250
    with pytest.raises(SimlinkError): bridge.adapter.player("x'); game.print('pwned")
    for action,args in [('set_daytime',{'value':'noon'}),('announce',{'text':"a' .. os.exit() .. '"}),('announce',{'text':'x'*201}),('pause',{'value':True})]:
        with pytest.raises(SimlinkError): bridge.adapter.command_for(action,args)
    item=bridge.propose('set_daytime',{'value':'day'},'Test')
    assert item['command']=='/silent-command game.surfaces.nauvis.daytime = 0'
    assert not any('daytime = 0' in r for r in fake_factorio[1])
    assert bridge.decide(item['id'],True)['status']=='response_received'
    assert fake_factorio[1].count('/silent-command game.surfaces.nauvis.daytime = 0')==1
    assert bridge.adapter.command_for('announce',{'text':'Bonjour, équipe !'})=="/silent-command game.print('[Simlink] Bonjour, équipe !')"


class FakeKrpc:
    class Control:
        throttle=0.0; sas=False; current_stage=3
        def activate_next_stage(self): self.current_stage-=1
    class Flight: mean_altitude=1234.56; speed=87.1
    class Body: name='Kerbin'
    class Orbit: body=None; apoapsis_altitude=80000.4; periapsis_altitude=-500.2
    class Vessel:
        name='Simlink 1'; situation='VesselSituation.flying'; control=None; orbit=None
        def flight(self): return FakeKrpc.Flight()
    class SpaceCenter: ut=42.0; active_vessel=None
    def __init__(self):
        self.space_center=FakeKrpc.SpaceCenter(); self.space_center.active_vessel=FakeKrpc.Vessel()
        self.control=self.space_center.active_vessel.control=FakeKrpc.Control()
        self.space_center.active_vessel.orbit=FakeKrpc.Orbit(); self.space_center.active_vessel.orbit.body=FakeKrpc.Body()
        self.closed=0
    def close(self): self.closed+=1


def test_kerbal_adapter(tmp_path):
    fake=FakeKrpc()
    config=Config('127.0.0.1',50000,'',tmp_path,'kerbal')
    bridge=Bridge(config,Kerbal(config,connection=lambda: fake))
    observed=bridge.adapter.observe()
    assert observed['vessel']=='Simlink 1' and observed['situation']=='flying' and observed['altitude_m']==1234.6 and observed['body']=='Kerbin'
    assert fake.closed==1
    for action,args in [('set_throttle',{'value':101}),('set_throttle',{'value':50.5}),('set_sas',{'value':'maybe'}),('next_stage',{}),('warp',{'value':1})]:
        with pytest.raises(SimlinkError): bridge.adapter.command_for(action,args)
    item=bridge.propose('set_throttle',{'value':50},'Test')
    assert fake.control.throttle==0.0
    assert bridge.decide(item['id'],True)['result']=='throttle=0.5'
    stage=bridge.propose('next_stage',{'value':'now'},'Test')
    assert bridge.decide(stage['id'],True)['result']=='stage=2'
    with pytest.raises(SimlinkError): bridge.adapter.player('Jeb')


def test_kerbal_requires_krpc_package(tmp_path, monkeypatch):
    import builtins
    real=builtins.__import__
    def fake_import(name,*args,**kwargs):
        if name=='krpc': raise ImportError
        return real(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',fake_import)
    with pytest.raises(SimlinkError, match='krpc'):
        Kerbal(Config('127.0.0.1',50000,'',tmp_path,'kerbal')).observe()
