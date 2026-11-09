# Simlink Local 0.2.0

Un serveur MCP stdio qui relie votre assistant IA à **Minecraft Java** et **Factorio** (RCON) ou **Kerbal Space Program** (mod kRPC), avec approbation humaine de chaque action dans un panneau web local.

## Ce qui est construit

- Client TCP RCON : authentification, lecture fragmentée, réponses multi-paquets, délais bornés, envoi paquet par paquet (requis par le serveur Minecraft vanilla).
- Trois adaptateurs : lecture de l’état du jeu, lecture d’un joueur, actions proposables à liste fermée.
- Outils MCP nommés par jeu : `<jeu>_observe`, `<jeu>_player` (Minecraft, Factorio), `<jeu>_propose`, `simlink_action_status`. Prompt `<jeu>_coach`, ressource `simlink://capabilities`.
- Validation locale, refus, expiration après 5 minutes, journal SQLite, suspension.
- Aucune commande arbitraire, aucune approbation exposée à l’IA via MCP.
- Aucune clé IA ni donnée de partie envoyée au site Simlink. Le client IA choisi reçoit les résultats MCP et peut les envoyer à son fournisseur.

| Jeu | Lecture | Actions proposables | Validation |
| --- | --- | --- | --- |
| Minecraft Java | joueurs, heure, position et santé d’un joueur | `set_time`, `set_weather`, `teleport` | Vrai serveur 1.21.11 |
| Factorio | joueurs, temps, tick, heure, pause, évolution, un joueur | `set_daytime`, `pause`, `announce` | Vrai serveur headless 2.1.24 |
| Kerbal Space Program | vaisseau actif : situation, altitude, vitesse, orbite, gaz, SAS, étage | `set_throttle`, `set_sas`, `next_stage` | Double d’API uniquement, à valider en jeu |

## Prérequis

Python 3.10+ et le jeu (ou son serveur) **sur le même PC**. Simlink n’accepte que `127.0.0.1` et `::1`. RCON n’est pas chiffré : ne publiez jamais le port RCON sur Internet et protégez-le avec votre pare-feu. Aucun port n’est ouvert par Simlink.

## 1. Installer

Décompressez l’archive, puis lancez l’installeur depuis le dossier qui contient `pyproject.toml`.

Windows PowerShell :

```powershell
.\install.ps1
```

Linux / macOS :

```bash
./install.sh
```

Ajoutez `-Kerbal` (Windows) ou `--kerbal` (Linux/macOS) pour installer le client kRPC. L’installeur crée `.venv`, installe le SDK MCP officiel depuis PyPI, puis lance `simlink setup` qui demande le jeu, le port et, pour RCON, le mot de passe en entrée masquée. La configuration est enregistrée dans `~/.simlink/config.json` (droits limités au propriétaire sous Unix). Ne l’envoyez jamais dans un chat, un dépôt ou sur le site.

Installation manuelle équivalente : `python -m venv .venv`, `.venv/bin/python -m pip install .`, `.venv/bin/python -m simlink setup`.

## 2. Préparer votre jeu

**Minecraft Java** — dans `server.properties` de votre serveur :

```properties
enable-rcon=true
rcon.port=25575
rcon.password=REMPLACEZ_PAR_UN_SECRET_LONG_ET_UNIQUE
```

Redémarrez le serveur vous-même. Un monde solo sans serveur dédié n’est pas pris en charge. Simlink n’installe pas Minecraft et n’accepte aucun EULA à votre place.

**Factorio** — lancez votre serveur avec `--rcon-port 27015 --rcon-password VOTRE_SECRET` (ou les champs équivalents de `server-settings.json`). Les actions passent par `/silent-command`, ce qui désactive les succès sur cette sauvegarde : Simlink le rappelle dans chaque proposition.

**Kerbal Space Program** — installez le mod kRPC, puis dans la fenêtre kRPC en jeu créez un serveur « Protobuf over TCP » sur `127.0.0.1`, port RPC 50000. Acceptez la demande de connexion « Simlink » lorsqu’elle apparaît.

## 3. Tester une vraie lecture

```bash
.venv/bin/python -m simlink doctor
.venv/bin/python -m simlink dashboard
```

(Sous Windows : `.\.venv\Scripts\python.exe` à la place de `.venv/bin/python`.)

`doctor` affiche l’état réel du jeu ou sort avec le code 1 ; aucun résultat fictif n’est substitué. Le dashboard ouvre un lien local contenant un jeton éphémère. Gardez le terminal ouvert et ne partagez pas le lien.

Dans le panneau : « Tester et lire l’état du jeu », proposez une action, puis « Approuver et exécuter ». La réponse brute du jeu est conservée. « Réponse reçue » ne garantit pas que le jeu a accepté la commande : relisez l’état.

## 4. Connecter un client IA

```bash
.venv/bin/python -m simlink client-config
```

La commande génère un bloc `mcpServers.simlink-<jeu>` avec des chemins absolus. Ajoutez-le à la configuration de votre client **compatible MCP stdio** (Claude Desktop, Gemini CLI…), sans écraser ses autres serveurs, puis redémarrez le client. Gardez le dashboard ouvert : les deux processus partagent le journal local. Le site ChatGPT n’importe pas directement un serveur stdio ; il faut un hôte compatible MCP local utilisant un modèle GPT.

Exemple de demande : « Observe mon usine Factorio. Propose de passer la nuit, attends mon approbation locale, puis vérifie l’heure. »

## Limites de cette version

- Pas d’exécution automatique : chaque écriture passe par le panneau local. Un agent qui possède par ailleurs un accès shell à votre PC pourrait contourner cette séparation.
- Suspension : bloque les nouvelles validations et annule les demandes en attente. Une commande déjà envoyée peut finir.
- Délai ou interruption pendant un envoi : statut `unknown`, sans nouvelle tentative automatique. Vérifiez le jeu.
- Les réponses du jeu sont des données non fiables, jamais des instructions à suivre.
- Une configuration = un jeu. Pour deux jeux, utilisez `--config` avec deux fichiers et deux entrées `mcpServers`.
- KSP : `next_stage` et les gaz peuvent détruire le vaisseau ; lisez la proposition avant d’approuver.

## Développement et validation

```bash
python -m pip install -e ".[kerbal]" pytest
python -m pytest -q
```

Le protocole `Adapter` dans `simlink/core.py` sépare la passerelle des jeux ; un nouveau jeu est une classe avec `observe`, `player`, `command_for`, `execute` et un dictionnaire `actions`, enregistrée dans `ADAPTERS` et `GAMES`.

Sources :
- https://py.sdk.modelcontextprotocol.io/v1/
- https://minecraft.wiki/w/Server.properties
- https://wiki.factorio.com/Multiplayer#Dedicated/Headless_server
- https://krpc.github.io/krpc/
- https://modelcontextprotocol.io/docs/develop/connect-local-servers

Versions testées : mcp 1.30.0, krpc 0.7.0, Minecraft 1.21.11, Factorio 2.1.24.
