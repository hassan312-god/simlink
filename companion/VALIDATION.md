# Validation v0.2.0 — 9 novembre 2026

Environnement de test : Linux, Python 3.13, SDK MCP 1.30.0, Java 21.
Résultat : 20 tests automatisés réussis, plus une validation sur deux serveurs de jeu réels.

## Serveurs réels

**Minecraft Java 1.21.11** (serveur officiel `server.jar` de Mojang, `enable-rcon=true`, monde plat) :
- `simlink doctor` retourne la vraie liste des joueurs et l’heure du monde.
- Propositions `set_time noon`, `set_weather rain`, `teleport` approuvées dans le panneau : réponses authentiques du serveur (« Set the time to 6000 », « Set the weather to rain », « No entity was found » pour un joueur absent), heure relue à 6000.
- **Bogue corrigé** : la version 0.1.0 échouait sur un vrai serveur (« Connexion RCON interrompue »). Le serveur vanilla ferme la connexion quand deux paquets RCON arrivent dans le même segment TCP, ce que la fixture de test 0.1.0 tolérait. Le client envoie désormais chaque paquet séparément et la fixture reproduit ce comportement.

**Factorio 2.1.24 headless** (`--rcon-port`, partie créée avec `--create`) :
- `doctor` lit joueurs, temps de partie, tick, heure de Nauvis, pause, évolution et vitesse.
- `set_daytime night` approuvé : `daytime` relu à 0,50 ; `announce` et `pause off` exécutés avec réponse vide (comportement normal de `/silent-command`).
- Le client MCP officiel découvre `factorio_observe`, `factorio_player`, `factorio_propose`, `simlink_action_status` et lit l’état en direct.

**Kerbal Space Program** : le jeu n’est pas disponible dans l’environnement de test. L’adaptateur est validé avec un double de l’API kRPC (lecture du vaisseau, gaz, SAS, étage, fermeture de connexion, rejet des paramètres hors bornes) et le client MCP découvre `kerbal_observe`, `kerbal_propose`, `simlink_action_status`. **À valider en jeu avec le mod kRPC 0.7.x.**

## Vérifié par les tests automatisés

- Framing RCON, authentification refusée, fragmentation TCP, réponses multi-paquets, fermeture sur paquets coalescés.
- Rejet de commandes libres, injections (retours à la ligne, sélecteurs, apostrophes Lua, coordonnées hors limites, nombres non entiers).
- Aucune écriture avant approbation ; une approbation ne s’exécute jamais deux fois, même en concurrence.
- Refus, expiration, suspension, journal partagé entre processus, changement de cible.
- Interruption réseau après envoi : résultat `unknown`, aucune répétition.
- API locale : jeton obligatoire, hôte et origine étrangers refusés.
- Configuration 0.1.0 sans champ `game` chargée comme Minecraft.

## Reste à valider

Windows et macOS, Claude Desktop et Gemini CLI avec un vrai modèle, KSP avec kRPC, serveurs Minecraft moddés (Paper, Fabric) et parties Factorio avec joueurs connectés.
