# Simlink Local 0.1.0

Première implémentation réelle : un serveur MCP stdio relié à Minecraft Java par RCON, avec approbations humaines dans un panneau web local.

## Ce qui est construit

- Client TCP RCON : authentification, lecture fragmentée, réponses multi-paquets et délais bornés.
- Outils MCP : joueurs/heure, position/santé d’un joueur, proposition de changement d’heure, météo ou téléportation, suivi d’action.
- Skill exposé comme prompt MCP `minecraft_coach` et ressource `simlink://capabilities`.
- Validation locale, refus, expiration après 5 minutes, journal SQLite, suspension.
- Aucune commande arbitraire, aucune approbation exposée à l’IA via MCP.
- Aucune clé IA ni donnée de partie envoyée au site Simlink. Le client IA choisi reçoit les résultats MCP et peut les envoyer à son fournisseur.

## Prérequis

Python 3.10+ et un serveur Minecraft Java que vous administrez, **sur le même PC**. Cette version ne pilote pas Minecraft Bedrock, un monde solo sans serveur dédié, ni les autres jeux du catalogue. Elle ne contrôle pas un personnage autonome.

RCON n’est pas chiffré. Simlink n’accepte que `127.0.0.1` et `::1`; ne publiez pas le port RCON sur Internet. Le serveur Minecraft peut écouter sur d’autres interfaces : protégez le port RCON avec votre pare-feu. Aucun port n’est ouvert automatiquement par Simlink.

## 1. Installer

Décompressez l’archive, puis ouvrez un terminal dans le dossier contenant `pyproject.toml`.

Windows PowerShell :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m simlink setup
```

Linux / macOS :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m simlink setup
```

L’installation récupère le SDK MCP officiel depuis PyPI. `setup` demande le mot de passe en entrée masquée, et l’enregistre dans `~/.simlink/config.json`. Les droits Unix sont limités au propriétaire ; sous Windows, gardez ce dossier dans votre profil utilisateur privé. N’envoyez pas ce fichier dans un chat, un dépôt ou sur le site. Le mot de passe n’est pas inclus dans la configuration MCP.

## 2. Préparer votre serveur

Dans le `server.properties` de votre serveur existant :

```properties
enable-rcon=true
rcon.port=25575
rcon.password=REMPLACEZ_PAR_UN_SECRET_LONG_ET_UNIQUE
```

Remplacez la valeur d’exemple et utilisez le même secret dans `simlink setup`. Redémarrez vous-même le serveur. Simlink n’installe pas le serveur et n’accepte aucun EULA à votre place. Ne modifiez pas vos réglages d’authentification Minecraft.

## 3. Tester une vraie lecture

Windows :

```powershell
.\.venv\Scripts\python.exe -m simlink doctor
.\.venv\Scripts\python.exe -m simlink dashboard
```

Linux / macOS :

```bash
.venv/bin/python -m simlink doctor
.venv/bin/python -m simlink dashboard
```

`doctor` doit retourner la liste réelle des joueurs et l’heure réelle. En cas d’échec il sort avec le code 1 ; aucun résultat fictif n’est substitué. Le dashboard ouvre un lien local contenant un jeton éphémère. Gardez le terminal ouvert. N’en partagez pas le lien.

Dans le panneau : cliquez « Tester et lire l’état du jeu », proposez `time set day`, puis « Approuver et exécuter ». La réponse brute du serveur est conservée. « Réponse reçue » ne garantit pas que Minecraft a accepté la commande : vérifiez son texte et relisez l’état du jeu. Pour une téléportation, vérifiez que la destination est sûre.

## 4. Connecter un client IA

Dans un deuxième terminal :

```powershell
.\.venv\Scripts\python.exe -m simlink client-config
```

ou sous Linux/macOS :

```bash
.venv/bin/python -m simlink client-config
```

La commande génère un bloc `mcpServers.simlink` avec des chemins absolus. Ajoutez ce bloc à la configuration de votre client **compatible avec les serveurs MCP locaux stdio**, sans écraser ses autres serveurs. Le client démarre le processus MCP ; gardez le dashboard ouvert dans le premier terminal. Les deux processus partagent le journal local.

Claude Desktop et Gemini CLI proposent ce type de connexion. Pour GPT, utilisez un hôte compatible avec les outils MCP locaux et configuré avec un modèle GPT, ou développez une orchestration API. Le site ChatGPT n’importe pas directement ce serveur stdio. Cette version ne contient pas de chat API Claude/Gemini/GPT, ni de tunnel MCP distant. Les formats d’import varient selon le client ; la sortie est du JSON `mcpServers`, pas un format universel pour tous les clients.

Exemple de demande à l’IA : « Observe mon serveur Minecraft. Propose de mettre le jour, attends mon approbation locale, puis vérifie l’heure. »

Les outils disponibles sont `minecraft_observe`, `minecraft_player`, `minecraft_propose`, `simlink_action_status`. L’IA ne peut pas approuver sa propre proposition par ces outils. Certains clients n’affichent pas les prompts MCP : vous pouvez utiliser les outils directement.

## Limites de cette version

- Adaptateur implémenté, testé avec un serveur de protocole RCON contrôlé et un client SDK MCP. **Validation en partie Minecraft et dans les clients IA de l’utilisateur encore nécessaire.**
- Pas d’exécution automatique : chaque écriture passe par le panneau local. Un agent qui possède par ailleurs un accès shell à votre PC pourrait contourner cette séparation ; ne lui accordez pas cet accès pour une session limitée aux outils Simlink.
- Suspension : bloque les nouvelles validations et annule les demandes en attente. Une commande déjà envoyée peut finir. Les lectures restent possibles.
- Délai ou interruption pendant un envoi : statut `unknown`, sans nouvelle tentative automatique. Vérifiez le jeu.
- Les réponses du jeu sont des données non fiables, jamais des instructions à suivre.
- Le panneau du site hébergé sert à télécharger et installer. Il ne peut pas atteindre le serveur Minecraft local. Le vrai tableau de bord est local.
- Journal : 100 dernières entrées affichées ; le fichier SQLite reste local. Aucun mot de passe enregistré dans les actions.

## Développement et validation

```bash
python -m pip install -e . pytest
python -m pytest -q
```

Le protocole `Adapter` dans `simlink/core.py` sépare la passerelle de Minecraft ; un autre jeu nécessite une implémentation qui possède une interface de lecture et d’action autorisée.

Sources :
- https://py.sdk.modelcontextprotocol.io/v1/
- https://docs.papermc.io/paper/reference/server-properties/
- https://geminicli.com/docs/tools/mcp-server/
- https://modelcontextprotocol.io/docs/develop/connect-local-servers

Version SDK utilisée et testée : mcp 1.30.0 (branche v1, version fixée dans pyproject.toml).
