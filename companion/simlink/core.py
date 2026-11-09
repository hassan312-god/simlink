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


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    password: str
    state_dir: Path

    def __post_init__(self):
        # This first release only talks to loopback: run it on the game server's PC.
        if self.host not in ('127.0.0.1', '::1'):
            raise SimlinkError('RCON doit être local : utilisez 127.0.0.1 ou ::1.')
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise SimlinkError('Port RCON invalide.')
        if not self.password or len(self.password.encode()) > 1024 or '\x00' in self.password:
            raise SimlinkError('Mot de passe RCON manquant ou invalide.')

    @property
    def target(self):
        return hashlib.sha256(f'{self.host}:{self.port}:{self.password}'.encode()).hexdigest()

    @classmethod
    def load(cls, path: Path):
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            return cls(raw['host'], raw['port'], raw['password'], path.resolve().parent)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SimlinkError('Configuration absente ou invalide. Lancez simlink setup.') from exc


class Rcon:
    """Bounded Source RCON framing, auth and multi-packet replies over loopback."""
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
                # A second harmless command provides an explicit reply boundary.
                sent = True
                sock.sendall(self.packet(2, 2, command) + self.packet(3, 2, 'list'))
                parts = []
                total = 0
                for _ in range(1024):
                    rid, kind, body = read()
                    if rid == 3 and kind == 0:
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
            raise SimlinkError('Serveur RCON inaccessible. Vérifiez le serveur, le port et enable-rcon.') from exc


class Adapter(Protocol):
    def observe(self) -> dict: ...
    def player(self, name: str) -> dict: ...
    def command_for(self, action: str, arguments: dict) -> str: ...
    def execute(self, command: str) -> str: ...


def player_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,16}', name):
        raise SimlinkError('Pseudo Minecraft invalide (1 à 16 caractères alphanumériques ou _).')
    return name


class Minecraft:
    def __init__(self, config: Config):
        self.rcon = Rcon(config)

    def execute(self, command):
        return self.rcon.execute(command)

    def observe(self):
        return {'game': 'Minecraft Java', 'players': self.execute('list'),
                'time': self.execute('time query daytime'), 'observed_at': time.time()}

    def player(self, name):
        name = player_name(name)
        return {'player': name, 'position': self.execute(f'data get entity {name} Pos'),
                'health': self.execute(f'data get entity {name} Health')}

    def command_for(self, action, arguments):
        if not isinstance(arguments, dict):
            raise SimlinkError('Les paramètres doivent être un objet.')
        if action == 'set_time' and set(arguments) == {'value'}:
            value = arguments['value']
            if value in ('day', 'noon', 'night', 'midnight'):
                return f'time set {value}'
        if action == 'set_weather' and set(arguments) == {'value'}:
            value = arguments['value']
            if value in ('clear', 'rain', 'thunder'):
                return f'weather {value}'
        if action == 'teleport' and set(arguments) == {'player', 'x', 'y', 'z'}:
            name = player_name(arguments['player'])
            for key, bound in [('x', 100000), ('y', 320), ('z', 100000)]:
                value = arguments[key]
                lower = -64 if key == 'y' else -bound
                if type(value) is not int or not lower <= value <= bound:
                    raise SimlinkError(f'Coordonnée {key} hors limites.')
            return f"tp {name} {arguments['x']} {arguments['y']} {arguments['z']}"
        raise SimlinkError('Action ou paramètres non autorisés. Actions : set_time, set_weather, teleport.')


class Bridge:
    def __init__(self, config: Config, adapter: Adapter | None = None):
        self.config = config
        self.adapter = adapter or Minecraft(config)
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
