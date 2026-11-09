# Simlink

Simlink est un projet de plateforme pour relier des jeux de simulation à des assistants IA grâce à des adaptateurs locaux et au protocole MCP. L’objectif est de découvrir des jeux et des mods compatibles, puis de permettre à un assistant de lire l’état du jeu et de proposer des actions que la personne valide.

## État actuel

| Jeu | Statut dans Simlink | Connexion |
| --- | --- | --- |
| Minecraft Java | Adaptateur 0.2.0, **validé sur un vrai serveur 1.21.11** | Serveur Minecraft Java local, RCON |
| Factorio | Adaptateur 0.2.0, **validé sur un vrai serveur headless 2.1.24** | Serveur Factorio local, RCON |
| Kerbal Space Program | Adaptateur 0.2.0, validé avec un double de l’API, à tester en jeu | Mod kRPC local |
| 15 autres jeux du catalogue | Concepts | Adaptateurs à développer |

Les nombres d’outils affichés pour les concepts sont des pistes de conception, pas des outils opérationnels. Aucun mod n’est fourni par Simlink.

## Ce qui fonctionne aujourd’hui

Le moteur `companion/` expose pour chaque jeu des outils MCP de lecture (`<jeu>_observe`, `<jeu>_player`), une proposition d’action à liste fermée (`<jeu>_propose`) et le suivi d’une action. Les écritures attendent une approbation dans un panneau local. Un installeur (`install.sh` / `install.ps1`) crée l’environnement et lance la configuration.

Voir le [guide d’installation](companion/README.md) et la [validation actuelle](companion/VALIDATION.md). Le site hébergé présente le catalogue et distribue le moteur ; il ne pilote pas directement un jeu installé sur votre ordinateur.

## Développement prévu

- Étudier, jeu par jeu, les interfaces autorisées : mod, API, plugin, serveur ou fichier local.
- Documenter les mods compatibles et leurs conditions d’installation avant de les afficher comme connectables.
- Valider KSP en jeu, puis Claude Desktop et Gemini CLI sur Windows et macOS.
- Ajouter de nouveaux adaptateurs MCP et vérifier chacun avec le jeu réel.
- Étudier l’usage de l’API Steam pour enrichir le catalogue ou la bibliothèque d’un utilisateur, selon les permissions disponibles.

L’API Steam ne fournit pas les fichiers des jeux et ne donne pas le droit de les redistribuer. Simlink ne contient pas les jeux commerciaux ni de launcher capable de contourner leurs plateformes de distribution.

## Démarrage du code

L’interface est dans `app/`, le catalogue dans `lib/games.ts`, et le moteur Python dans `companion/`. Le projet web utilise pnpm ; le moteur local nécessite Python 3.10 ou plus. Les commandes détaillées et les prérequis Minecraft figurent dans [companion/README.md](companion/README.md).
