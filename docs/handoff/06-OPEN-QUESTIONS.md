
# Questions ouvertes et vérifications

## Décisions que seul le propriétaire peut prendre
1. Mode de travail avec Mistral (A, B ou C dans `05-TOOLS-AND-WORKFLOWS.md`) et organisation multi-IA.
2. Nom définitif de l'add-on (« CNC Control » est provisoire).
3. Licence définitive (LGPL-2.1 ou plus choisie sous réserve) et mention de l'auteur.
4. Place de la CAO : OmniFab, SolidCraft (fork ou extension) ou FreeCAD ; le propriétaire a déjà retenu FreeCAD pour le contrôle machine seulement.
5. Où vit le dossier de pilotage commun à plusieurs projets : ici (`docs/handoff/`) pour l'instant ; un dépôt dédié, éventuellement privé, serait plus logique si le dossier grossit.
6. Version de FreeCAD à installer sur le poste du propriétaire (Snap, AppImage, autre) afin que l'agent puisse inspecter l'API réelle.

## À vérifier avant d'implémenter (réf. `../FRAMING.md` section 9)
Mécanisme de découverte d'un post-processeur tiers ; objets temporaires dans la vue 3D ; numérotation des versions (1.2 ou 26.3) et présence des fichiers .fcm dans la 1.1 ; version de PySide et roues disponibles pour Python 3.14 ; installation depuis un dépôt personnel par l'Addon Manager ; mode de vérification, G38.2, G10 L20, tampon de réception et commandes temps réel de GRBL 1.1 ; licence de pyserial ; licence et compatibilité de LinuxCNC avec une add-on LGPL ; limites actuelles du plan gratuit de Mistral.

## Informations que Claude n'a pas
Résultats des audits d'OmniFab n°4 et n°5, étude de SolidCraft, plan d'organisation multi-IA discuté avec Mistral. Le propriétaire peut les déposer dans `docs/handoff/external/` pour que l'orchestrateur les prenne en compte.
# Fichier 2/2 : documents de référence du projet FreeCAD CNC Control

Contenu : AGENTS.md (règles pour les agents de code, en anglais), docs/FRAMING.md (dossier de cadrage), docs/LAUNCH_PROMPT.md (plan E0 à E16), docs/PROGRESS.md (état d'avancement). Dépôt : https://github.com/RaphOlivier/freecad-cnc-control

