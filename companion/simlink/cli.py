import argparse
import getpass
import json
import os
from pathlib import Path
import sys
from .core import Bridge, Config, SimlinkError


def main():
    parser = argparse.ArgumentParser(description='Simlink local — Minecraft Java RCON / MCP')
    parser.add_argument('--config', type=Path, default=Path.home() / '.simlink' / 'config.json')
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('setup', help='Configuration interactive locale')
    sub.add_parser('doctor', help='Test réel de connexion RCON, sans écriture dans le jeu')
    sub.add_parser('mcp', help='Serveur MCP sur stdio')
    sub.add_parser('client-config', help='Configuration JSON à importer dans un client MCP stdio')
    dash = sub.add_parser('dashboard', help='Ouvrir le panneau local d’approbation')
    dash.add_argument('--port', type=int, default=8766)
    dash.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    path = args.config.expanduser().resolve()
    try:
        if args.mode == 'setup':
            if path.exists():
                raise SimlinkError(f'Configuration déjà présente : {path}. Modifiez ce fichier localement pour la changer.')
            print('Exécutez Simlink sur le même PC que votre serveur Minecraft Java.')
            print('Le port RCON doit rester fermé à Internet. Le mot de passe sera enregistré localement.')
            port = int(input('Port RCON [25575] : ').strip() or '25575')
            password = getpass.getpass('Mot de passe rcon.password (masqué) : ')
            config = Config('127.0.0.1', port, password, path.parent)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Exclusive creation prevents accidental overwrite and sets Unix permissions.
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as out:
                json.dump({'host': config.host, 'port': config.port, 'password': config.password}, out, indent=2)
            print('Configuration enregistrée. Lancez simlink doctor, puis simlink dashboard.')
            return
        if args.mode == 'client-config':
            # An absolute executable works even when a GUI host has no activated virtualenv.
            print(json.dumps({'mcpServers': {'simlink': {'command': sys.executable,
                'args': ['-m', 'simlink', '--config', str(path), 'mcp']}}}, indent=2))
            return
        config = Config.load(path)
        if args.mode == 'mcp':
            from .mcp_server import create_server
            create_server(config).run(transport='stdio')
        elif args.mode == 'doctor':
            print(json.dumps(Bridge(config).adapter.observe(), ensure_ascii=False, indent=2))
        elif args.mode == 'dashboard':
            from .dashboard import serve
            serve(Bridge(config), args.port, not args.no_browser)
    except (SimlinkError, ValueError, OSError) as exc:
        # Errors stay off stdout so stdio MCP framing is never polluted.
        print('Simlink : ' + (str(exc) if isinstance(exc, SimlinkError) else 'Vérifiez le port, les permissions des fichiers et les paramètres locaux.'), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
