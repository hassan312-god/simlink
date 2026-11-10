# Simlink

Simlink est un projet de plateforme pour relier des jeux de simulation à des assistants IA grâce à des adaptateurs locaux et au protocole MCP. L’objectif est de découvrir des jeux et des mods compatibles, puis de permettre à un assistant de lire l’état du jeu et de proposer des actions que la personne valide.

## État actuel

| Jeu | Statut dans Simlink | Connexion |
| --- | --- | --- |
| Minecraft Java | Premier adaptateur implémenté en version 0.1.0 | Serveur Minecraft Java local administré par l’utilisateur, RCON et serveur MCP local |
| Cities: Skylines II | Concept au catalogue | Adaptateur à développer |
| Microsoft Flight Simulator | Concept au catalogue | Adaptateur à développer |
| Euro Truck Simulator 2 | Concept au catalogue | Adaptateur à développer |
| Stardew Valley | Concept au catalogue | Adaptateur à développer |
| Kerbal Space Program | Concept au catalogue | Adaptateur à développer |
| Factorio | Concept au catalogue | Adaptateur à développer |
| Satisfactory | Concept au catalogue | Adaptateur à développer |
| Transport Fever 2 | Concept au catalogue | Adaptateur à développer |
| Planet Zoo | Concept au catalogue | Adaptateur à développer |
| Subnautica | Concept au catalogue | Adaptateur à développer |
| RimWorld | Concept au catalogue | Adaptateur à développer |
| Oxygen Not Included | Concept au catalogue | Adaptateur à développer |
| No Man’s Sky | Concept au catalogue | Adaptateur à développer |
| Dyson Sphere Program | Concept au catalogue | Adaptateur à développer |

Les nombres d’outils affichés pour les quatorze concepts sont des pistes de conception, pas des outils opérationnels. Aucun mod de ces jeux n’est actuellement fourni ou intégré par Simlink.

## Ce qui fonctionne aujourd’hui

Le moteur `companion/` propose quatre outils MCP pour Minecraft Java : observer les joueurs et l’heure, lire des informations sur un joueur, proposer une action et suivre son statut. Les actions d’écriture demandent une approbation dans un panneau local. La communication avec le serveur Minecraft passe par RCON sur l’ordinateur de l’utilisateur.

Le protocole RCON, le serveur MCP et le mécanisme d’approbation ont été vérifiés avec des tests automatisés. Une validation sur une vraie partie Minecraft et avec les clients IA de l’utilisateur reste à faire. Le site hébergé présente le catalogue et distribue le moteur local ; il ne pilote pas directement un jeu installé sur ton ordinateur.

Voir le [guide d’installation](companion/README.md) et la [validation actuelle](companion/VALIDATION.md). Le [site Simlink](https://simlink-hub.buzzybean129.chatgpt.site/) présente l’interface.

## Développement prévu

- Étudier, jeu par jeu, les interfaces autorisées : mod, API, plugin, serveur ou fichier local.
- Documenter les mods compatibles et leurs conditions d’installation avant de les afficher comme connectables.
- Ajouter de nouveaux adaptateurs MCP et vérifier chacun avec le jeu réel.
- Étudier l’usage de l’API Steam pour enrichir le catalogue ou la bibliothèque d’un utilisateur, selon les permissions disponibles.

L’API Steam ne fournit pas les fichiers des jeux et ne donne pas le droit de les redistribuer. Simlink ne contient pas les jeux commerciaux ni de launcher capable de contourner leurs plateformes de distribution.

## Démarrage du code

L’interface est dans `app/`, le catalogue dans `lib/games.ts`, et le moteur Python dans `companion/`. Le projet web utilise pnpm ; le moteur local nécessite Python 3.10 ou plus. Les commandes détaillées et les prérequis Minecraft figurent dans [companion/README.md](companion/README.md).
