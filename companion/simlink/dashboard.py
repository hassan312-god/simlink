import hmac
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .core import Bridge, SimlinkError


def make_server(bridge, port=8766):
    token = secrets.token_urlsafe(32)
    html = Path(__file__).with_name('dashboard.html').read_bytes()
    mutation_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        timeout = 10
        def log_message(self, *args):
            pass

        def respond(self, code, value, content_type='application/json; charset=utf-8'):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            host = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != host:
                self.respond(403, {'error': 'Hôte refusé.'})
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                self.respond(403, {'error': 'Origine refusée.'})
                return False
            return True

        def authorized(self):
            if not self.allowed():
                return False
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied, 'Bearer ' + token):
                self.respond(401, {'error': 'Ouvrez le lien complet affiché par simlink dashboard.'})
                return False
            return True

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                if self.allowed():
                    self.respond(200, html, 'text/html; charset=utf-8')
                return
            if not self.authorized():
                return
            try:
                if path == '/api/state':
                    self.respond(200, {'halted': bridge.halted(), 'actions': bridge.actions(), 'target': f'{bridge.config.host}:{bridge.config.port}',
                                       'game': bridge.config.label, 'presets': [{'action': key, 'label': value['label'], 'values': value['values']} for key, value in bridge.adapter.actions.items() if value['values']]})
                elif path == '/api/observe':
                    self.respond(200, bridge.adapter.observe())
                else:
                    self.respond(404, {'error': 'Route introuvable.'})
            except SimlinkError as exc:
                self.respond(502, {'error': str(exc)})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    raise SimlinkError('Corps de requête invalide.')
                if self.headers.get('Content-Type') != 'application/json':
                    raise SimlinkError('Content-Type JSON requis.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise SimlinkError('Objet JSON requis.')
                path = urlsplit(self.path).path
                # Serializes stop and human approvals; no commands are auto-retried.
                with mutation_lock:
                    if path == '/api/propose':
                        result = bridge.propose(data.get('action'), data.get('arguments'), data.get('reason'))
                    elif path == '/api/decide':
                        if type(data.get('approve')) is not bool:
                            raise SimlinkError('Décision invalide.')
                        result = bridge.decide(data.get('id'), data['approve'])
                    elif path == '/api/stop':
                        result = bridge.stop(True)
                    elif path == '/api/resume':
                        result = bridge.stop(False)
                    else:
                        self.respond(404, {'error': 'Route introuvable.'})
                        return
                self.respond(200, result)
            except (SimlinkError, ValueError, TypeError) as exc:
                message = str(exc) if isinstance(exc, SimlinkError) else 'Requête invalide.'
                self.respond(400, {'error': message})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server, token


def serve(bridge, port=8766, browser=True):
    server, token = make_server(bridge, port)
    url = f'http://127.0.0.1:{server.server_port}/#token={token}'
    print('Simlink local — gardez cette fenêtre ouverte. Ctrl+C pour arrêter.')
    print('Lien local privé (ne pas partager) : ' + url, flush=True)
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
