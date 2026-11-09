# Validation v0.1.0 — 9 novembre 2026

Environnement de test : Linux, Python 3.12, SDK MCP 1.30.0.
Résultat : 16 tests automatisés réussis.

Vérifié :
- Framing RCON TCP, authentification refusée, fragmentation TCP et assemblage de plusieurs réponses.
- Rejet de commandes libres, injections de retours à la ligne, sélecteurs de joueurs et coordonnées invalides.
- Aucune écriture avant approbation humaine ; une approbation ne peut être exécutée deux fois, même simultanément.
- Refus, expiration, suspension et partage du journal entre processus.
- Changement de configuration serveur : les anciennes demandes ne peuvent plus être approuvées.
- Interruption réseau après envoi : résultat inconnu, aucune répétition automatique.
- API locale : jeton obligatoire, rejet d’origines et d’hôtes étrangers, observation et approbation.
- Client MCP officiel en sous-processus : initialisation, découverte des quatre outils, lecture, proposition, résultat, erreur, prompt et ressource.

Limite : le serveur utilisé dans les tests est une fixture de protocole contrôlée, pas une instance du jeu Minecraft. Le lancement sur le serveur du joueur, les spécificités de sa version Minecraft, les environnements Windows/macOS et l’utilisation depuis Claude Desktop ou Gemini CLI restent à valider. Les tests ne prouvent pas une compatibilité universelle.
