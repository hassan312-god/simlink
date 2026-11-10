# Simlink - vision produit et installation sans Python

**Document de cadrage produit et technique - 10 novembre 2026**  
**Statut : proposition de réalisation, avec état actuel distingué de la cible.**

## 1. Ce que je veux construire

Simlink est une application de bureau pour PC et ordinateur portable qui relie des jeux de simulation installés sur le PC de l'utilisateur à un assistant IA. **Parcours cible : avoir le jeu installé, installer Simlink, choisir ce jeu et laisser Simlink installer/configurer son mod ou connecteur compatible.** L'utilisateur saisit ensuite sa propre clé API OpenAI, Anthropic ou Google, fixe un objectif et décide du niveau d'autonomie accordé. L'IA observe l'état du jeu, planifie, agit via un connecteur propre au jeu, vérifie le résultat et poursuit l'objectif dans les limites choisies.

Le site présente les jeux, leurs images officielles, leurs informations, les connecteurs et les instructions. Le compagnon de bureau exécute le moteur local. Simlink ne distribue pas les jeux commerciaux et ne promet pas un connecteur pour un jeu qui n'a pas été développé et testé.

### Expérience souhaitée

1. Télécharger un installateur Simlink pour Windows, puis pour macOS et Linux.
2. Installer et ouvrir Simlink sans installer Python, ouvrir un terminal ou créer un script.
3. Laisser Simlink détecter les jeux installés localement et distinguer « détecté », « possédé », « compatible » et « connecteur prêt ». Ajouter manuellement un dossier si nécessaire.
4. Sélectionner un jeu ; Simlink vérifie sa version et son installation, propose le mod ou connecteur compatible, demande l'accord pour modifier le dossier du jeu, télécharge le paquet vérifié, installe et teste la connexion. L'utilisateur ne crée aucun script et ne copie aucun fichier à la main. Aucune modification cachée des fichiers du jeu.
5. Choisir Claude, Gemini ou GPT ; coller la clé API dans l'application de bureau. La clé est enregistrée localement de façon protégée, jamais dans le site public ni dans un dépôt.
6. Décrire un objectif, par exemple « construire une ferme capable de produire X ressources » ; voir les outils, permissions, coûts possibles et limites avant de lancer.
7. Suivre les observations, actions, résultats et erreurs dans un journal. Pouvoir mettre en pause, reprendre et arrêter immédiatement.

## 2. Décision : aucun Python à manipuler par les utilisateurs

**Choix retenu : Electron pour l'application de bureau et Rust pour le moteur local.** Electron reprend l'interface du site et gère les fenêtres, l'installation et les mises à jour. Un exécutable Rust livré avec l'application détecte les jeux, installe les mods compatibles, gère les outils MCP, les permissions et les objectifs. Le processus Electron communique avec ce moteur local par un canal privé contrôlé. Il n'y a **aucune dépendance Python dans le produit distribué**, ni script, terminal ou configuration MCP à créer par l'utilisateur. Le prototype Python actuel sert de référence fonctionnelle et de tests durant la migration ; il n'est pas livré aux utilisateurs.

Pour les mises à jour, produire des versions signées avec `electron-builder` et `electron-updater` : l'application vérifie, télécharge puis installe une nouvelle version après accord et redémarrage. Les paquets incluent le moteur Rust correspondant, afin que l'interface et le protocole local restent compatibles. Sur Linux, choisir explicitement une cible de distribution et sa stratégie de mise à jour ; le module `autoUpdater` natif d'Electron n'y fournit pas de prise en charge intégrée.

**Livrables nécessaires :** installateurs signés par système et architecture, moteur empaqueté, démarrage et arrêt automatiques, mises à jour, désinstallation propre, journal de diagnostic et tests sur ordinateur vierge. Le site actuel qui distribue un ZIP et affiche des commandes Python devra devenir une page de téléchargement et un guide visuel.

**Choix pour Minecraft Java :** le connecteur actuel requiert un serveur administré par l'utilisateur avec RCON local. Pour atteindre le parcours cible « jeu installé seulement », il faut développer un **mod côté Minecraft Java**, compatible avec un chargeur et des versions explicitement pris en charge. Ce mod observe la partie et expose des actions bornées au moteur Simlink local, y compris en monde solo si la version et le chargeur le permettent. L'application installe le mod dans le bon dossier, vérifie son intégrité et la compatibilité, puis demande de redémarrer le jeu si nécessaire. Le pont RCON actuel reste une étape technique provisoire ; il ne satisfait pas encore le parcours cible.

**Règle de compatibilité :** pouvoir installer un mod ouvre une voie technique, mais ne garantit pas que Simlink puisse lire tous les états ou piloter toutes les actions. Il faut développer et tester un adaptateur par jeu, version et chargeur, et respecter les restrictions du jeu et de sa plateforme. Un jeu qui interdit ou ne permet pas ce type de mod ne sera pas marqué compatible.

## 3. Architecture cible

| Composant | Rôle | Où il tourne |
| --- | --- | --- |
| Site Simlink | Catalogue, fiches, documentation et téléchargements | Web |
| Application Simlink Desktop (Electron) | Installation, réglages, écrans, mises à jour et journal | PC de l'utilisateur |
| Moteur local Rust embarqué | Détection des jeux, mods, outils MCP, permissions, objectifs et exécution | PC de l'utilisateur |
| Mod / adaptateur par jeu | Lecture d'état et actions explicites selon l'interface permise par ce jeu | Jeu local et moteur Simlink |
| Orchestrateur d'objectifs | Boucle observer → planifier → agir → vérifier, budget et reprise | Application locale |
| API du fournisseur IA | Génération de décisions à partir des observations et outils autorisés | Fournisseur choisi par l'utilisateur |

Le protocole MCP sert à exposer des outils à des clients compatibles. **Une clé API seule ne connecte pas un jeu** : il faut l'adaptateur du jeu et un orchestrateur qui appelle le modèle, exécute les outils, vérifie le résultat et répète. Pour une expérience « coller la clé puis jouer », Simlink Desktop doit intégrer cet orchestrateur. Une connexion MCP à Claude Desktop ou Gemini CLI peut rester une option avancée, avec configuration générée automatiquement. Pour GPT, il faut intégrer son API dans Simlink ou utiliser un client qui sait joindre les outils locaux ; le site ChatGPT n'est pas un import universel du serveur stdio.

## 4. Autonomie avec garde-fous réglables

Trois modes visibles : **Observation** (lecture seule), **Assisté** (validation des actions) et **Autonome limité** (actions présélectionnées dans un budget et une durée). L'utilisateur choisit les outils autorisés, la zone/partie, le nombre maximal d'actions, le plafond de dépenses API et la durée. Les opérations sensibles (suppression de sauvegarde, achats, modifications système, commandes arbitraires) sont exclues par défaut et demandent des règles distinctes.

Chaque cycle suit : observer l'état réel ; générer un plan court ; valider les arguments contre le schéma et les permissions ; exécuter une action ; relire l'état ; comparer au critère de réussite ; continuer, demander de l'aide ou arrêter. Journal local horodaté, bouton d'arrêt permanent, traitement des erreurs, anti-boucle, délai entre actions et sauvegarde de l'objectif. Le modèle ne peut ni augmenter ses propres permissions ni approuver une action qu'il a proposée.

**Premier test de bout en bout :** sur un serveur Minecraft Java de test, un objectif borné utilisant uniquement les outils réellement disponibles. Le moteur actuel lit l'état et propose quelques actions RCON soumises à approbation ; il ne contrôle pas encore un personnage ni une mission autonome complète. Un objectif nécessitant déplacement, collecte ou construction doit attendre un adaptateur de jeu plus riche.

## 5. Données de jeux et Steam

L'API Web Steam peut enrichir un catalogue et, selon les conditions de visibilité, renvoyer les jeux possédés d'un compte. Elle ne livre pas les fichiers des jeux. La détection d'une installation sur le PC doit être faite localement par l'application, avec le consentement de l'utilisateur ; l'accès aux mods et le lancement dépendent des outils et droits propres à chaque jeu et plateforme. Ne pas marquer un jeu « installé » ou « jouable » sur la seule base d'une fiche Steam.

Chaque fiche distingue : **jeu réel**, **données vérifiées**, **installation locale détectée ou non**, **connecteur testé ou concept**, **mod nécessaire**, **fonctions accessibles**, **limites**. Le catalogue actuel contient quinze jeux, mais seul l'adaptateur Minecraft Java 0.1 existe et sa validation sur une vraie partie reste à faire.

## 6. Parcours et écrans à produire

- **Accueil desktop :** logo Simlink rouge/orange unique, sidebar, recherche, hero visuel, catalogue avec jaquettes réelles, état des fournisseurs sans faux « connecté ».
- **Fiche jeu :** une seule identité de marque dans la sidebar, titre et statut, première capture ou vidéo officielle comme hero interactif, miniatures, données vérifiées, configuration PC, statut du connecteur et actions permises.
- **Bibliothèque :** jeux locaux détectés, favoris séparés, état de l'installation, source, version et chemin contrôlé par l'utilisateur.
- **Connecteurs / mods :** compatibilité par version du jeu, prérequis, installation guidée, diagnostic, permissions et désinstallation.
- **Fournisseurs IA :** saisie et test local de clé API, modèle, plafond de coût et suppression de la clé.
- **Objectifs :** saisie du but, mode d'autonomie, aperçu des actions autorisées, exécution, journal et arrêt.
- **Paramètres :** dossiers de jeux, sauvegardes, mises à jour, vie privée et diagnostics.

## 7. Étapes de réalisation et critères de validation

**Étape A - application sans Python.** Construire le shell Electron, migrer le noyau nécessaire en Rust, empaqueter les deux dans un installateur signé et configurer une chaîne de mises à jour testée. Un nouveau PC Windows installe, démarre, met à jour, ferme et désinstalle Simlink sans Python installé, sans terminal et sans copie manuelle de configuration MCP.

**Étape B - connecter Minecraft réellement.** Construire et tester un mod Minecraft Java pour les versions/chargeurs choisis, avec installation guidée depuis Simlink, échange local avec le moteur, lecture d'une vraie partie solo, proposition et validation d'une action, journal et diagnostic. Valider le parcours sur un PC avec Minecraft installé et sans Python ni serveur configuré manuellement. Le connecteur RCON peut servir de banc d'essai durant la transition.

**Étape C - clés API et orchestration.** Ajouter un fournisseur à la fois, stockage local protégé, test de clé sans l'afficher, appels API avec plafond, conversation/outils et journal. Aucun secret dans le navigateur public, les logs ou les rapports d'erreur.

**Étape D - première mission autonome bornée.** Objectif réalisable avec les outils Minecraft existants ou avec un adaptateur enrichi, limite d'actions et de durée, pause/arrêt, vérification du résultat dans une vraie partie. Ne déclarer le mode autonome « prêt » qu'après cet essai.

**Étape E - autres jeux.** Prioriser par faisabilité et interfaces de modding officielles, développer/tester un adaptateur par jeu et version, puis seulement afficher « connecteur disponible ».

## 8. Ce qui existe aujourd'hui

Le dépôt contient un site Next.js avec catalogue et pages détaillées, ainsi qu'un moteur Python local pour Minecraft Java (RCON + MCP + approbation). Le guide actuel demande Python 3.10+, plusieurs commandes, un serveur Minecraft avec RCON et une configuration du client MCP. Les tests automatisés valident des composants, mais **l'installation sans Python, le mod Minecraft solo, les clés IA dans Simlink, le lancement direct des jeux et les objectifs autonomes ne sont pas encore livrés**. Le présent document décrit la cible et un chemin concret pour y arriver.

## Références techniques

- Dépôt Simlink : https://github.com/hassan312-god/simlink
- Mises à jour des applications Electron : https://www.electronjs.org/docs/latest/tutorial/updates
- Distribution et mises à jour electron-builder : https://www.electron.build/docs/features/auto-update/
- Stockage local chiffré Electron safeStorage : https://www.electronjs.org/docs/latest/api/safe-storage
- Sécurité des processus Electron : https://www.electronjs.org/docs/latest/tutorial/security
- SDK MCP TypeScript et transport local stdio : https://ts.sdk.modelcontextprotocol.io/server
- Steamworks GetOwnedGames et conditions de visibilité : https://partner.steamgames.com/doc/webapi/IPlayerService

*Ce document est une spécification de produit. Les maquettes servent de direction artistique ; leurs mentions « installé » ou « jouer » ne prouvent aucune fonction existante.*
