
# État d'avancement et suite

## Fait (au 2026-11-10)
1. Entretien de cadrage en 16 vagues de questions ; toutes les décisions sont dans `../FRAMING.md`.
2. Trois livrables produits : dossier de cadrage (`../FRAMING.md`), consignes d'agent (`../../AGENTS.md`), prompt de lancement (`../LAUNCH_PROMPT.md`, plan E0 à E16).
3. Dépôt public créé : https://github.com/RaphOlivier/freecad-cnc-control. Contenu au moment de la vérification de Claude : une branche `main`, un commit « Initial commit », un fichier `README.md` [V].
4. Poste du propriétaire : Kubuntu, git, gh (connecté à GitHub), unzip, Python 3.14.3 installés. Claude Code est installé (2.1.319) mais inutilisable : il exige un forfait payant ou une clé API, et le propriétaire reste sur un compte gratuit.
5. Pas de code, pas de FreeCAD vérifié sur le poste du propriétaire (version installée inconnue).

## À faire, dans l'ordre
1. Le propriétaire applique ce paquet de passation dans le dépôt (commande dans la réponse de Claude : décompresser, `git add`, `git commit`, `git push`).
2. L'orchestrateur choisit le mode de travail (voir `05-TOOLS-AND-WORKFLOWS.md`) : conversation dans le navigateur avec commandes collées par le propriétaire, ou agent en ligne de commande si l'accès gratuit le permet.
3. Vérifier sur le poste du propriétaire : `freecadcmd --version` (ou `freecad.cmd`) et la version de FreeCAD disponible ; décider de l'installation (Snap, AppImage, dépôt officiel) [?].
4. Lancer l'étape E0 de `../LAUNCH_PROMPT.md` : squelette du dépôt, intégration continue sur 3 systèmes, licence provisoire, `package.xml` provisoire.
5. Étape E1 : inspection de l'API FreeCAD installée (post-processeurs, objets temporaires, Qt) et consignation dans `docs/DECISIONS.md`. C'est la condition pour ne rien deviner ensuite.
6. Étapes E2 à E8 : le cœur de communication, testable sans FreeCAD ; c'est le meilleur point de départ si FreeCAD pose problème.
7. Procédures manuelles n°1 à n°4 : le propriétaire les lance et rapporte les résultats.

## Pièges à connaître dès le départ
- Python 3.14 sur le poste du propriétaire : les roues PySide pour cette version peuvent manquer [?] ; décider si les tests Qt tournent sous une version de Python plus ancienne ou dans FreeCAD.
- Le faux GRBL doit fonctionner sous Windows : pas de pseudo-terminal ni de `socat` là-bas, d'où des transports en mémoire ou par socket.
- Le périmètre du jalon 1 est large pour un seul jalon : imposer des points d'étape testables (après E6, E8, E11).

