
# FreeCAD CNC Control : le projet en bref

Référence complète : `../FRAMING.md` (28 décisions D-01 à D-28, hypothèses H-01 à H-09). Ce fichier en est le résumé pour un lecteur pressé.

## Idée
Un add-on FreeCAD (atelier « CNC Control », panneau ancré) qui pilote des machines CNC directement depuis FreeCAD, en réutilisant l'existant : atelier CAM, post-processeurs, et plus tard configurations de machine et outils. On ne modifie pas le cœur de FreeCAD.

## Vision à long terme (à garder en tête pour l'architecture, pas à faire maintenant)
- Machines : fraiseuse 3 axes, tour, brodeuse, découpeuse laser, plasma. FreeCAD couvre bien le fraisage [V] ; laser/plasma partiellement [P] ; tour et brodeuse presque pas [P].
- Contrôleurs : GRBL, FluidNC, Smoothieware, puis Marlin, g2core, LinuxCNC, Duet, Klipper (proposition [P]).
- Mode LinuxCNC : si FreeCAD et l'add-on sont installés sur une machine LinuxCNC, piloter directement via le système (module Python `linuxcnc`, HAL, fichiers INI), comme remplaçant du logiciel Axis.
- Configuration de machine inspirée de LinuxCNC : moteurs, cinématique (cartésienne, polaire, CoreXY…), axes, limites, vitesses, accélérations, homing.
- Liaison RS-232 avec détection sûre des paramètres (commandes inoffensives, aucun mouvement, avec confirmation du propriétaire).
- Jog continu et contrôle de job sur tous les contrôleurs.

## Jalon 1 (un seul jalon, livré en une fois)
GRBL 1.1 par liaison série : connexion, état et position, ordres temps réel, jog (pas fixes et continu), streaming par comptage de caractères, alarmes sans reprise automatique, $H, $X, lecture de $$, décalages G54… et G92, surcharges de vitesse, macros, sonde Z puis bords X/Y, envoi d'un fichier ou du Job CAM sélectionné via un post-processeur GRBL propre à l'add-on, marqueur et avancement en objets temporaires de la vue 3D, contrôles avant job (limites, confirmation, mode de vérification GRBL), pause automatique sur perte de liaison, journal série.
Réussite : un job CAM complet tourne de bout en bout sur émulateur avec un test automatique. Si ça glisse : sacrifier sonde, puis macros, puis surcharges.

## Architecture retenue
- `core/` Python pur (protocole, streamer, analyse G-code, interface « contrôleur », transports) ; `worker/` processus séparé qui tient la liaison série avec battement de vie (pause automatique si l'interface ne répond plus) ; `freecad_adapter/` seul à importer FreeCAD (isole FreeCAD 1.1 et 1.2 dev) ; `gui/` Qt sans hypothèse GRBL ; `testing/` faux GRBL en Python.
- Configuration de machine : JSON maison, alignable plus tard sur les fichiers .fcm de FreeCAD.
- pyserial embarqué avec sa licence (la liste de paquets autorisés de l'Addon Manager ne le contient pas, version lue [V]).
- Langues : code, commits et docs de dépôt en anglais ; textes d'interface traduisibles.

## Tests
Tout simulé en intégration continue (GitHub Actions) : faux GRBL Python sur Linux, Windows, macOS ; simulateur GRBL compilé sous Linux ; Qt hors-écran. Pas de test automatique avec le vrai FreeCAD : à la place, procédures manuelles que le propriétaire lance à chaque étape clé, et vérification de l'API dans le code FreeCAD installé (jamais deviner).

## Sécurité
Aucun mouvement sans action explicite ni homing automatique à la connexion ; arrêt toujours accessible même si l'interface se fige ; alarme : arrêt du streaming et aucune reprise sans action ; refus du job si le G-code sort des limites lues dans les réglages GRBL ; confirmation explicite ; aucun agent ne touche une machine réelle.

## Licence et publication
Usage personnel d'abord, code publiable ensuite ; dépôt public dédié ; LGPL-2.1 ou plus envisagée (FreeCAD est en LGPL-2.0 ou plus [V]) sous réserve de la vérification des licences. Publication dans le catalogue officiel de l'Addon Manager : hors jalon 1.

## Feuille de route après le jalon 1 (ordre fixé par le propriétaire)
1. Liaison RS-232 avec détection des paramètres ; 2. autres contrôleurs (FluidNC, Smoothieware…) ; 3. configuration de machine et cinématiques ; 4. mode LinuxCNC. Premier type de machine à ajouter : découpeuse laser. Le propriétaire a demandé que l'agent décide seul de la suite après le jalon 1, dans le respect des garde-fous.

