from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sqlite3
import struct
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SimlinkError(Exception):
    pass


GAMES = {
    'minecraft': {'label': 'Minecraft Java', 'transport': 'rcon', 'port': 25575},
    'factorio': {'label': 'Factorio', 'transport': 'rcon', 'port': 27015},
    'kerbal': {'label': 'Kerbal Space Program', 'transport': 'krpc', 'port': 50000},
}


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    password: str
    state_dir: Path
    game: str = 'minecraft'

    def __post_init__(self):
        if self.game not in GAMES:
            raise SimlinkError('Jeu inconnu. Jeux pris en charge : ' + ', '.join(GAMES))
        # Every release so far only talks to loopback: run Simlink on the game's PC.
        if self.host not in ('127.0.0.1', '::1'):
            raise SimlinkError('La connexion doit être locale : utilisez 127.0.0.1 ou ::1.')
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise SimlinkError('Port invalide.')
        if self.transport == 'rcon':
            if not self.password or len(self.password.encode()) > 1024 or '\x00' in self.password:
                raise SimlinkError('Mot de passe RCON manquant ou invalide.')
        elif not isinstance(self.password, str) or '\x00' in self.password:
            raise SimlinkError('Mot de passe invalide.')

    @property
    def transport(self):
        return GAMES[self.game]['transport']

    @property
    def label(self):
        return GAMES[self.game]['label']

    @property
    def target(self):
        return hashlib.sha256(f'{self.game}:{self.host}:{self.port}:{self.password}'.encode()).hexdigest()

    @classmethod
    def load(cls, path: Path):
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            # Configurations written by 0.1.0 have no game field and were Minecraft only.
            return cls(raw['host'], raw['port'], raw.get('password', ''), path.resolve().parent, raw.get('game', 'minecraft'))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SimlinkError('Configuration absente ou invalide. Lancez simlink setup.') from exc


class Rcon:
    """Bounded Source RCON framing, auth and multi-packet replies over loopback.

    Packets are sent one at a time: the vanilla Minecraft server closes the
    connection when two requests arrive in the same TCP segment.
    """
    def __init__(self, config: Config, timeout: float = 5):
        self.config = config
        self.timeout = timeout

    @staticmethod
    def packet(request_id: int, kind: int, body: str):
        data = struct.pack('<ii', request_id, kind) + body.encode('utf-8') + b'\0\0'
        return struct.pack('<i', len(data)) + data

    @staticmethod
    def exact(sock, length, deadline=None):
        result = bytearray()
        while len(result) < length:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                sock.settimeout(remaining)
            part = sock.recv(length - len(result))
            if not part:
                raise SimlinkError('Connexion RCON interrompue.')
            result.extend(part)
        return bytes(result)

    @classmethod
    def receive(cls, sock, deadline=None):
        size, = struct.unpack('<i', cls.exact(sock, 4, deadline))
        if not 10 <= size <= 4 * 1024 * 1024:
            raise SimlinkError('Paquet RCON invalide.')
        data = cls.exact(sock, size, deadline)
        if data[-2:] != b'\0\0':
            raise SimlinkError('Terminaison RCON invalide.')
        request_id, kind = struct.unpack('<ii', data[:8])
        return request_id, kind, data[8:-2]

    def execute(self, command: str):
        if not command or len(command.encode()) > 2048 or any(c in command for c in '\r\n\0'):
            raise SimlinkError('Commande invalide.')
        sent = False
        deadline = time.monotonic() + self.timeout
        try:
            with socket.create_connection((self.config.host, self.config.port), self.timeout) as sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                def read():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    sock.settimeout(remaining)
                    return self.receive(sock, deadline)
                sock.sendall(self.packet(1, 3, self.config.password))
                for _ in range(3):
                    rid, kind, _ = read()
                    if rid == -1:
                        raise SimlinkError('Authentification RCON refusée.')
                    if rid == 1 and kind == 2:
                        break
                else:
                    raise SimlinkError('Réponse d’authentification RCON invalide.')
                sent = True
                sock.sendall(self.packet(2, 2, command))
                rid, kind, body = read()
                if rid != 2 or kind != 0:
                    raise SimlinkError('Identifiant de réponse RCON inattendu.')
                parts = [body]
                total = len(body)
                # A second harmless request, sent only after the first reply, marks the
                # end of a possibly fragmented response without coalescing packets.
                sock.sendall(self.packet(3, 2, self.boundary()))
                for _ in range(1024):
                    rid, kind, body = read()
                    if rid == 3:
                        return b''.join(parts).decode('utf-8', errors='replace')
                    if rid != 2 or kind != 0:
                        raise SimlinkError('Identifiant de réponse RCON inattendu.')
                    total += len(body)
                    if total > 1024 * 1024:
                        raise SimlinkError('Réponse RCON trop volumineuse.')
                    parts.append(body)
                raise SimlinkError('Trop de fragments RCON.')
        except (OSError, SimlinkError) as exc:
            # Never expose the password or raw OS details; never retry a write.
            if sent:
                raise SimlinkError('Réponse RCON non confirmée : la commande a pu être exécutée. Vérifiez le jeu avant de recommencer.') from exc
            if isinstance(exc, SimlinkError):
                raise
            raise SimlinkError('Serveur RCON inaccessible. Vérifiez le serveur, le port et l’activation de RCON.') from exc

    def boundary(self):
        return '/version' if self.config.game == 'factorio' else 'list'


class Adapter(Protocol):
    label: str
    actions: dict  # action -> {'label': str, 'values': [(value, label)] | None}

    def observe(self) -> dict: ...
    def player(self, name: str) -> dict: ...
    def command_for(self, action: str, arguments: dict) -> str: ...
    def execute(self, command: str) -> str: ...


def player_name(name, pattern=r'[A-Za-z0-9_]{1,16}', message='Pseudo invalide (1 à 16 caractères alphanumériques ou _).'):
    if not isinstance(name, str) or not re.fullmatch(pattern, name):
        raise SimlinkError(message)
    return name


def single_value(action, arguments, allowed):
    if set(arguments) != {'value'} or arguments['value'] not in allowed:
        raise SimlinkError(f'{action} attend {{"value": ' + '|'.join(map(str, allowed)) + '}.')
    return arguments['value']


class Minecraft:
    label = 'Minecraft Java'
    actions = {
        'set_time': {'label': 'Changer l’heure', 'values': [('day', 'Jour'), ('noon', 'Midi'), ('night', 'Nuit'), ('midnight', 'Minuit')]},
        'set_weather': {'label': 'Changer la météo', 'values': [('clear', 'Ciel clair'), ('rain', 'Pluie'), ('thunder', 'Orage')]},
        'teleport': {'label': 'Téléporter un joueur', 'values': None},
    }

    def __init__(self, config: Config):
        self.rcon = Rcon(config)

    def execute(self, command):
        return self.rcon.execute(command)

    def observe(self):
        return {'game': self.label, 'players': self.execute('list'),
                'time': self.execute('time query daytime'), 'observed_at': time.time()}

    def player(self, name):
        name = player_name(name)
        return {'player': name, 'position': self.execute(f'data get entity {name} Pos'),
                'health': self.execute(f'data get entity {name} Health')}

    def command_for(self, action, arguments):
        if not isinstance(arguments, dict):
            raise SimlinkError('Les paramètres doivent être un objet.')
        if action == 'set_time':
            return 'time set ' + single_value(action, arguments, ['day', 'noon', 'night', 'midnight'])
        if action == 'set_weather':
            return 'weather ' + single_value(action, arguments, ['clear', 'rain', 'thunder'])
        if action == 'teleport' and set(arguments) == {'player', 'x', 'y', 'z'}:
            name = player_name(arguments['player'])
            for key, bound in [('x', 100000), ('y', 320), ('z', 100000)]:
                value = arguments[key]
                lower = -64 if key == 'y' else -bound
                if type(value) is not int or not lower <= value <= bound:
                    raise SimlinkError(f'Coordonnée {key} hors limites.')
            return f"tp {name} {arguments['x']} {arguments['y']} {arguments['z']}"
        raise SimlinkError('Action ou paramètres non autorisés. Actions : set_time, set_weather, teleport.')


class Factorio:
    """Factorio headless server over its built-in RCON.

    Reads use console commands and `/silent-command rcon.print(...)` with fixed Lua.
    Writes are fixed Lua templates; `/silent-command` disables achievements on the
    save, which the proposal text states.
    """
    label = 'Factorio'
    actions = {
        'set_daytime': {'label': 'Changer l’heure (Nauvis)', 'values': [('day', 'Jour'), ('night', 'Nuit')]},
        'pause': {'label': 'Mettre en pause / reprendre', 'values': [('on', 'Pause'), ('off', 'Reprendre')]},
        'announce': {'label': 'Message dans le chat', 'values': None},
    }
    STATE = ("/silent-command rcon.print(helpers.table_to_json({tick=game.tick, "
             "players=#game.connected_players, daytime=game.surfaces.nauvis.daytime, paused=game.tick_paused, "
             "evolution=game.forces.enemy.get_evolution_factor('nauvis'), speed=game.speed}))")

    def __init__(self, config: Config):
        self.rcon = Rcon(config)

    def execute(self, command):
        return self.rcon.execute(command)

    def observe(self):
        state = self.execute(self.STATE).strip()
        try:
            parsed = json.loads(state) if state else {}
        except ValueError:
            parsed = {'raw': state}
        return {'game': self.label, 'players': self.execute('/players online').strip(),
                'time': self.execute('/time').strip(), 'state': parsed, 'observed_at': time.time()}

    def player(self, name):
        name = player_name(name, r'[A-Za-z0-9_.-]{1,60}', 'Nom de joueur Factorio invalide.')
        lua = (f"/silent-command local p=game.get_player('{name}') if p then rcon.print(helpers.table_to_json("
               "{name=p.name, online=p.connected, surface=p.surface.name, position=p.position, "
               "health=p.character and p.character.health or nil})) else rcon.print('absent') end")
        raw = self.execute(lua).strip()
        try:
            return {'player': name, 'data': json.loads(raw)}
        except ValueError:
            return {'player': name, 'data': raw}

    def command_for(self, action, arguments):
        if not isinstance(arguments, dict):
            raise SimlinkError('Les paramètres doivent être un objet.')
        if action == 'set_daytime':
            value = single_value(action, arguments, ['day', 'night'])
            return f"/silent-command game.surfaces.nauvis.daytime = {'0' if value == 'day' else '0.5'}"
        if action == 'pause':
            value = single_value(action, arguments, ['on', 'off'])
            return f"/silent-command game.tick_paused = {'true' if value == 'on' else 'false'}"
        if action == 'announce' and set(arguments) == {'text'}:
            text = arguments['text']
            if not isinstance(text, str) or not re.fullmatch(r"[A-Za-z0-9 À-ÿ.,!?:;()-]{1,200}", text):
                raise SimlinkError('Texte limité à 200 caractères simples, sans guillemets ni apostrophes.')
            return "/silent-command game.print('[Simlink] " + text + "')"
        raise SimlinkError('Action ou paramètres non autorisés. Actions : set_daytime, pause, announce.')


class Kerbal:
    """Kerbal Space Program through the kRPC mod (RPC port, no stream connection).

    Needs the optional `krpc` package. `connection` lets tests inject a fake client.
    """
    label = 'Kerbal Space Program'
    actions = {
        'set_throttle': {'label': 'Régler les gaz (%)', 'values': [(0, '0 %'), (25, '25 %'), (50, '50 %'), (100, '100 %')]},
        'set_sas': {'label': 'SAS', 'values': [('on', 'Activer'), ('off', 'Désactiver')]},
        'next_stage': {'label': 'Étage suivant', 'values': [('now', 'Déclencher')]},
    }

    def __init__(self, config: Config, connection=None):
        self.config = config
        self._connection = connection

    def client(self):
        if self._connection is not None:
            return self._connection()
        try:
            import krpc  # noqa: WPS433
        except ImportError as exc:
            raise SimlinkError('Le paquet krpc est requis : pip install "simlink-local[kerbal]".') from exc
        try:
            return krpc.connect(name='Simlink', address=self.config.host, rpc_port=self.config.port, stream_port=None, timeout=5)
        except (OSError, ConnectionError) as exc:
            raise SimlinkError('Serveur kRPC inaccessible. Lancez KSP avec le mod kRPC et démarrez son serveur.') from exc

    def observe(self):
        conn = self.client()
        try:
            sc = conn.space_center
            vessel = sc.active_vessel
            if vessel is None:
                return {'game': self.label, 'vessel': None, 'ut': sc.ut, 'observed_at': time.time()}
            flight = vessel.flight()
            orbit = vessel.orbit
            return {'game': self.label, 'vessel': vessel.name, 'situation': str(vessel.situation).split('.')[-1],
                    'body': orbit.body.name, 'altitude_m': round(flight.mean_altitude, 1),
                    'speed_m_s': round(flight.speed, 1), 'apoapsis_m': round(orbit.apoapsis_altitude, 1),
                    'periapsis_m': round(orbit.periapsis_altitude, 1), 'throttle': vessel.control.throttle,
                    'sas': vessel.control.sas, 'stage': vessel.control.current_stage, 'ut': sc.ut,
                    'observed_at': time.time()}
        finally:
            self.close(conn)

    def player(self, name):
        raise SimlinkError('KSP n’a pas de liste de joueurs : utilisez l’observation du vaisseau actif.')

    def command_for(self, action, arguments):
        if not isinstance(arguments, dict):
            raise SimlinkError('Les paramètres doivent être un objet.')
        if action == 'set_throttle' and set(arguments) == {'value'}:
            value = arguments['value']
            if type(value) is not int or not 0 <= value <= 100:
                raise SimlinkError('set_throttle attend un entier de 0 à 100.')
            return f'throttle {value}'
        if action == 'set_sas':
            return 'sas ' + single_value(action, arguments, ['on', 'off'])
        if action == 'next_stage':
            single_value(action, arguments, ['now'])
            return 'stage'
        raise SimlinkError('Action ou paramètres non autorisés. Actions : set_throttle, set_sas, next_stage.')

    def execute(self, command):
        conn = self.client()
        try:
            vessel = conn.space_center.active_vessel
            if vessel is None:
                raise SimlinkError('Aucun vaisseau actif.')
            control = vessel.control
            if command.startswith('throttle '):
                control.throttle = int(command.split()[1]) / 100
                return f'throttle={control.throttle}'
            if command.startswith('sas '):
                control.sas = command.endswith('on')
                return f'sas={control.sas}'
            if command == 'stage':
                control.activate_next_stage()
                return f'stage={control.current_stage}'
            raise SimlinkError('Commande KSP inconnue.')
        finally:
            self.close(conn)

    @staticmethod
    def close(conn):
        try:
            conn.close()
        except Exception:
            pass


ADAPTERS = {'minecraft': Minecraft, 'factorio': Factorio, 'kerbal': Kerbal}


def make_adapter(config: Config) -> Adapter:
    return ADAPTERS[config.game](config)


class Bridge:
    def __init__(self, config: Config, adapter: Adapter | None = None):
        self.config = config
        self.adapter = adapter or make_adapter(config)
        config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db_path = config.state_dir / 'simlink.sqlite3'
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY, target TEXT NOT NULL, action TEXT NOT NULL,
                    arguments TEXT NOT NULL, command TEXT NOT NULL, reason TEXT NOT NULL,
                    status TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
                    result TEXT, finished REAL
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO settings VALUES ('halted', '0');
            ''')
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def halted(self):
        with self.db() as db:
            return db.execute("SELECT value FROM settings WHERE key='halted'").fetchone()[0] == '1'

    def stop(self, halted=True):
        with self.db() as db:
            db.execute("UPDATE settings SET value=? WHERE key='halted'", ('1' if halted else '0',))
            if halted:
                db.execute("UPDATE actions SET status='cancelled', finished=? WHERE status='pending'", (time.time(),))
        return {'halted': halted, 'note': 'Les commandes déjà envoyées ne peuvent pas être annulées.'}

    def propose(self, action, arguments, reason):
        command = self.adapter.command_for(action, arguments)
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 1000:
            raise SimlinkError('Motif requis (1 à 1000 caractères).')
        now = time.time()
        action_id = str(uuid.uuid4())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT value FROM settings WHERE key='halted'").fetchone()[0] == '1':
                raise SimlinkError('Actions suspendues par l’utilisateur.')
            db.execute("UPDATE actions SET status='expired',finished=? WHERE status='pending' AND expires<?", (now, now))
            if db.execute("SELECT count(*) FROM actions WHERE status='pending'").fetchone()[0] >= 50:
                raise SimlinkError('50 propositions en attente. Traitez-les dans le panneau local.')
            db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (action_id, self.config.target, action, json.dumps(arguments), command, reason,
                        'pending', now, now + 300, None, None))
        return {'id': action_id, 'status': 'pending', 'command': command, 'expires': now + 300,
                'next_step': 'Attendre la validation humaine dans le panneau Simlink local. Ne pas prétendre que la commande a été exécutée.'}

    @staticmethod
    def public(row):
        result = dict(row)
        result.pop('target', None)
        result['arguments'] = json.loads(result['arguments'])
        return result

    def actions(self):
        now = time.time()
        with self.db() as db:
            db.execute("UPDATE actions SET status='expired',finished=? WHERE status='pending' AND expires<?", (now, now))
            # A crashed process may have sent a command. Never make it pending again.
            db.execute("UPDATE actions SET status='unknown',result='Exécution interrompue : vérifier le jeu avant de recommencer.',finished=? WHERE status='executing' AND finished<?", (now, now - 30))
            rows = db.execute('SELECT * FROM actions WHERE target=? ORDER BY created DESC LIMIT 100', (self.config.target,)).fetchall()
        return [self.public(row) for row in rows]

    def action(self, action_id):
        for row in self.actions():
            if row['id'] == action_id:
                return row
        raise SimlinkError('Action introuvable dans les 100 dernières actions de cette connexion.')

    def decide(self, action_id, approve):
        now = time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM actions WHERE id=? AND target=?', (action_id, self.config.target)).fetchone()
            if row is None or row['status'] != 'pending':
                raise SimlinkError('Action absente ou déjà traitée.')
            if row['expires'] < now:
                db.execute("UPDATE actions SET status='expired',finished=? WHERE id=?", (now, action_id))
                return {'id': action_id, 'status': 'expired'}
            if not approve:
                db.execute("UPDATE actions SET status='rejected',finished=? WHERE id=?", (now, action_id))
                return {'id': action_id, 'status': 'rejected'}
            if db.execute("SELECT value FROM settings WHERE key='halted'").fetchone()[0] == '1':
                raise SimlinkError('Actions suspendues.')
            command = self.adapter.command_for(row['action'], json.loads(row['arguments']))
            if command != row['command']:
                raise SimlinkError('Commande modifiée : créez une nouvelle proposition.')
            db.execute("UPDATE actions SET status='executing',finished=? WHERE id=?", (now, action_id))
        try:
            response = self.adapter.execute(command)
            # A reply may be a game-level error: keep raw reply, do not assert success.
            status, result = 'response_received', response
        except SimlinkError as exc:
            status, result = 'unknown', str(exc)
        except Exception:
            status, result = 'unknown', 'Erreur inattendue. Vérifiez le jeu avant de recommencer.'
        with self.db() as db:
            db.execute('UPDATE actions SET status=?,result=?,finished=? WHERE id=?', (status, result, time.time(), action_id))
        return {'id': action_id, 'status': status, 'result': result}
