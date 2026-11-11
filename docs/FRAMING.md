
# Dossier de cadrage — CNC Control pour FreeCAD (nom provisoire)

Version du 2026-11-10 (issu de l'entretien de cadrage du 2026-11-09). Légende de confiance : [V] vérifié (source citée), [P] probable, [?] à vérifier dans le code installé ou la documentation.

## 1. Contexte et objectifs

Add-on FreeCAD pour piloter des machines CNC depuis FreeCAD, en réutilisant l'existant (atelier CAM, post-processeurs, plus tard configurations de machine et outils) sans modifier le cœur de FreeCAD.

Vision à long terme : fraiseuse 3 axes, tour, brodeuse, laser, plasma ; contrôleurs GRBL, FluidNC, Smoothieware et autres ; mode LinuxCNC (remplaçant d'Axis) ; configuration de machine (type de moteur, cinématique, limites, vitesses, accélérations, homing) ; liaison RS-232 avec détection des paramètres ; jog et contrôle de job sur tous les contrôleurs.

Jalon 1 : voir section 2. Usage perso d'abord, code publiable ensuite (dépôt GitHub public dédié, distinct d'OmniFab).

## 2. Spécification du jalon 1

Périmètre (un seul jalon livré en une fois) :
- GRBL 1.1 uniquement, liaison série.
- Connexion et déconnexion ; état et position ; ordres temps réel (pause, reprise, arrêt/reset).
- Jog : pas fixes et jog continu (arrêt au relâchement ou à la perte de focus).
- Envoi de G-code en streaming par comptage de caractères du tampon de réception [?].
- Alarmes et erreurs : le streaming s'arrête, l'alarme s'affiche, rien ne reprend sans action explicite.
- $H (homing), $X (déverrouillage), lecture des réglages $$ (affichage seul).
- Décalages de travail : G54 à G59 stockés par GRBL (G10 L20 [?]) et G92, au choix de l'utilisateur ; mise à zéro des axes.
- Surcharges de vitesse (feed override).
- Macros : listes de lignes G-code dans un fichier de l'add-on ; confirmation explicite avant toute macro contenant un mouvement.
- Sonde : palpage Z plus bords X/Y (G38.2 [P]) ; épaisseur de plaque et distance max réglables ; confirmation avant chaque palpage (hypothèse H-06).
- Source du G-code : fichier quelconque, ou Job CAM sélectionné envoyé via un post-processeur GRBL propre à l'add-on.
- Visualisation : marqueur de position et avancement du trajet déjà usiné, en objets temporaires de la vue 3D (jamais enregistrés dans le document). Le tracé est calculé depuis le G-code ; les noms d'opérations sont lus dans les commentaires du post-processeur.
- Contrôles avant job : refus automatique si le G-code sort des limites de la machine (lues dans $$) ; confirmation explicite ; mode de vérification de GRBL (sans mouvement) proposé avant le job réel [?] ; simulateur logiciel.
- Perte de liaison pendant un job : pause automatique ; reprise possible après reconnexion, avec confirmation explicite.
- Journal des échanges série, activable, en fichiers tournants.

Critère de réussite : un job CAM complet (Job CAM simulé ou G-code fabriqué représentatif) tourne de bout en bout sur l'émulateur, avec un test automatique.

Ordre de sacrifice si le calendrier glisse : sonde, puis macros, puis surcharges de vitesse.

Hors-jalon : autres contrôleurs, LinuxCNC, cinématiques, RS-232, autres types de machines, GRBL 0.9 et grblHAL, 4e axe, publication dans le catalogue officiel de l'Addon Manager.

## 3. Registre des décisions

| ID | Décision |
|---|---|
| D-01 | Add-on sous forme d'atelier FreeCAD « CNC Control » avec panneau ancré (connexion, état, jog, job) |
| D-02 | Jalon 1 : un seul jalon livré en une fois |
| D-03 | GRBL 1.1 uniquement dans le jalon 1 |
| D-04 | Streaming par comptage de caractères |
| D-05 | Alarme : arrêt du streaming, affichage, aucune reprise sans action explicite |
| D-06 | Usage perso d'abord, code publiable ; dépôt GitHub public dédié, distinct d'OmniFab |
| D-07 | Licence LGPL-2.1 ou plus (sous réserve de la vérification des licences, section 7) |
| D-08 | Nom descriptif et neutre, « CNC Control » provisoire |
| D-09 | Systèmes : Linux, Windows, macOS ; FreeCAD 1.1 stable et 1.2 dev |
| D-10 | pyserial embarqué dans le dépôt avec sa licence ; ajout à la liste autorisée de l'Addon Manager à demander plus tard |
| D-11 | G-code : fichier quelconque ou Job CAM via post-processeur GRBL propre à l'add-on |
| D-12 | Tracé et avancement calculés depuis le G-code ; noms d'opérations lus dans les commentaires |
| D-13 | Marqueur et avancement en objets temporaires de la vue 3D |
| D-14 | Processus séparé qui tient la liaison série, avec battement de vie ; pause automatique si l'interface cesse de répondre |
| D-15 | Configuration de machine du jalon 1 : JSON propre à l'add-on, alignable plus tard sur .fcm |
| D-16 | Journal série activable, fichiers tournants |
| D-17 | Contrôles avant job : refus hors limites + confirmation ; vérification GRBL puis job réel ; simulateur logiciel |
| D-18 | Perte de liaison : pause automatique, reprise après reconnexion avec confirmation |
| D-19 | Tests : faux GRBL Python (3 systèmes) + simulateur compilé (Linux) en CI ; tout simulé ; Qt hors-écran avec PySide installé à part |
| D-20 | Procédure manuelle lancée par l'utilisateur dans FreeCAD à chaque étape clé |
| D-21 | Exemples de G-code et de Jobs fabriqués par l'agent ; FreeCAD installé sur la machine de l'agent |
| D-22 | Feuille de route après jalon 1 : RS-232, autres contrôleurs, configuration/cinématiques, LinuxCNC ; laser en premier type de machine ; non figée |
| D-23 | L'agent enchaîne seul sur le jalon suivant, dans le respect des garde-fous |
| D-24 | Arrêt après 3 échecs sur une même étape ou à la limite d'usage ; reprise via le journal |
| D-25 | Git : branche de travail dédiée, un commit par petite étape testée, push seulement sur cette branche, jamais de force-push ni de modification de main ; l'utilisateur fusionne |
| D-26 | Journal d'avancement en Markdown dans le dépôt ; REPORT.md final ; AGENTS.md (et CLAUDE.md qui y renvoie) |
| D-27 | Macros : lignes G-code dans un fichier de l'add-on, confirmation avant mouvement |
| D-28 | Mise à zéro : décalages stockés (G54…) et G92 au choix |

## 4. Hypothèses (choisies par l'architecte, à corriger)

- H-01 Aucun mouvement ni homing automatique à la connexion ; ordres temps réel envoyés sans passer par la file de streaming [P].
- H-02 Port choisi par l'utilisateur dans une liste ; vitesse par défaut 115200 [P], réglable.
- H-03 L'agent peut lancer FreeCAD en ligne de commande pour inspecter l'API installée (lecture seule), jamais pour piloter une machine.
- H-04 L'enchaînement sur le RS-232 est écrit et testé uniquement sur ports virtuels ; l'essai réel est une procédure manuelle de l'utilisateur.
- H-05 Intégration continue sur GitHub Actions ; textes d'interface en anglais, traduisibles.
- H-06 Sonde X/Y : mêmes confirmations que Z, avant chaque cycle.
- H-07 Espace de noms Python `freecad/cnc_control/` (disposition vue dans la documentation Addon Academy [V] pour le vendoring ; à confirmer pour un atelier [?]).
- H-08 Canal entre l'interface et le processus série : tubes standard (stdin/stdout) avec messages JSON ligne à ligne, portables sur les 3 systèmes ; battement de vie toutes les 500 ms, pause automatique après 2 s sans signal (valeurs réglables).
- H-09 Aucun port réel n'est ouvert par les outils de test ni par l'agent ; seuls les transports virtuels (mémoire, pseudo-terminal, socket) sont autorisés dans les tests.

## 5. Étude de l'existant FreeCAD

| Brique | Ce qu'elle fait | Utilisation depuis l'add-on | Limites | Confiance et sources | Décision |
|---|---|---|---|---|---|
| Version stable | 1.1.3 publiée le 2026-07-25 ; 1.1 sortie le 2026-03-24 | Cible principale | La 1.2 (dev) est visée aussi | [V] https://wiki.freecad.org/Download ; notes de version 1.1 | — |
| Atelier CAM (anciennement Path, renommé en 1.0) | Génère des trajectoires en « G-code interne » (commandes `Path.Command` dans des objets Path) ; la traduction vers le dialecte machine se fait par post-processeur | Lire/appeler le post-processeur d'un Job ; ne pas dépendre des objets pour le tracé | API qui change vite ; documentation partiellement ancienne | [V] https://wiki.freecad.org/CAM_scripting | Adapter (un seul point d'accès : couche d'adaptation) |
| Post-processeurs | Convertissent le G-code interne en dialecte (GRBL, LinuxCNC…) | Post-processeur GRBL propre à l'add-on, avec commentaires d'opération | Mécanisme d'enregistrement/découverte d'un post-processeur tiers non vérifié | [V] pour le rôle ; [?] pour le mécanisme | À créer (s'inspirer du post-processeur GRBL de FreeCAD, licence compatible LGPL) |
| Bibliothèque d'outils | Nouveau système « Better Tool Library » en 1.1 (éditeur et sélecteur de toolbits) | Hors-jalon | Refonte récente | [V] notes de version 1.1 | Réutiliser plus tard |
| Machines (.fcm) | Fichiers JSON : cinématique, limites, vitesses, post-processeur recommandé | Hors-jalon ; aligner le JSON maison dessus | Annoncées pour « 1.2 » par Addon Academy ; les préférences CAM parlent de « 26.3 » : numérotation à clarifier. Probablement absentes de la 1.1 stable | [V] https://freecad.github.io/Addon-Academy/Topics/Types/Machines ; [?] version exacte | Adapter plus tard |
| Dépôt FreeCAD/Machines | Collection communautaire de machines, distribuée via l'Addon Manager | Source d'exemples | — | [V] https://github.com/FreeCAD/Machines | Réutiliser plus tard |
| Addon Manager | Installe des add-ons depuis des dépôts (types Workbench, Macro, Preference Pack, Bundle, Other) ; métadonnées dans `package.xml` | Distribution de l'add-on depuis un dépôt Git personnel | Dépendances Python via pip limitées à une liste autorisée ; la version lue ne contient pas pyserial (liste marquée « avant 1.0 ») | [V] https://github.com/FreeCAD/AddonManager ; https://github.com/FreeCAD/FreeCAD-addons/blob/master/ALLOWED_PYTHON_PACKAGES.txt ; https://freecad.github.io/Addon-Academy/Topics/Dependencies/Vendoring | Réutiliser |
| Interface Qt | FreeCAD embarque une liaison Qt pour Python | Atelier, panneau ancré | Version de PySide à vérifier (1.1 et 1.2) | [?] | Réutiliser |
| Vue 3D | Affichage des objets du document | Marqueur et trajet en objets temporaires | Mécanisme d'objets temporaires non vérifié | [?] | À créer, après vérification |
| Simulateur CAM | Simulation de l'usinage | Hors-jalon | — | [V] présence (page CAM) | Ne pas réutiliser dans le jalon 1 |
| Ligne de commande | `freecad.cmd` dans le paquet Snap | Inspection de l'API par l'agent (H-03) | Nom du binaire variable selon l'installation | [V] https://snapcraft.io/freecad | Réutiliser |

### Couverture par type de machine (FreeCAD seul)
- Fraiseuse 3 axes : couverte par CAM [V].
- Laser, plasma : contours et gravure utilisables, sans gestion dédiée de puissance, perçage ou hauteur de torche [P].
- Tour : pas d'opérations de tournage dans CAM [P].
- Brodeuse : hors G-code, formats propres (DST, PES…), rien dans FreeCAD [P].

### Familles de contrôleurs à couvrir à terme (proposition, [P])
GRBL/grblHAL ; FluidNC ; Smoothieware ; Marlin ; TinyG/g2core ; LinuxCNC ; Duet (RepRapFirmware) ; Klipper (via son API). Les contrôleurs propriétaires fermés ne sont pas ciblés.

## 6. Existant externe (inspiration, pas de copie de code)
- Émulateurs : grbl-sim (GRBL compilé sur PC, pseudo-terminal via socat) https://github.com/mfkiwl/grbl-sim ; grblHAL Simulator (mêmes principes, option de connexion telnet brute) https://github.com/grblHAL/Simulator [V]. Windows : pas de socat, d'où le faux GRBL Python et des transports de test en mémoire ou par socket.
- Envoi de G-code : Universal G-code Sender (Java), bCNC (Python), CNCjs, Candle, GRBL-Plotter [V, page de comparaison du wiki https://github.com/winder/Universal-G-Code-Sender/wiki, adresse exacte de la page à retrouver].
- LinuxCNC : module Python `linuxcnc` (état, commandes, erreurs, lecture INI) [V] https://linuxcnc.org/docs/2.8/html/config/python-interface.html ; Axis est un composant GPL v2+ [V, en-tête de source].

## 7. Licences (à finaliser avant publication)
- FreeCAD : LGPL-2.0-or-later [V, https://snapcraft.io/freecad].
- Projets d'inspiration : bCNC GPLv2 ; GRBL, Candle, GRBL-Plotter GPLv3 ; CNCjs MIT [V, tableau du wiki UGS, à reconfirmer dans les dépôts] ; UGS à vérifier.
- pyserial : licence à vérifier (probablement BSD) ; l'embarquer exige de joindre sa licence.
- LinuxCNC : composants sous GPL ; la compatibilité avec une add-on LGPL qui importe son module Python est à analyser avant le jalon LinuxCNC [?].
- Règle : aucun code copié de projets GPL ; s'en inspirer seulement. Tout code tiers (même MIT) exige un accord.

## 8. Risques connus
1. Périmètre large pour un seul jalon livré en une fois : points d'étape testables imposés dans le plan.
2. Processus série séparé : protocole supplémentaire à tester sur 3 systèmes.
3. Tout simulé en CI : risque d'un add-on qui passe ses tests mais échoue dans FreeCAD ; atténué par la procédure manuelle et la vérification de l'API dans le code installé.
4. API FreeCAD changeante (1.1 contre 1.2) : isolée dans la couche d'adaptation.
5. Enchaînement automatique sur le RS-232 (matériel réel) : borné par H-04 et H-09.
6. Un arrêt logiciel ne remplace pas un arrêt d'urgence matériel : à écrire dans la documentation utilisateur.

## 9. Points à vérifier dans le code ou les sources
Mécanisme du post-processeur propre ; fichiers .fcm et numérotation 1.2 / 26.3 ; mode de vérification de GRBL ; G38.2 ; G10 L20 ; taille du tampon de réception et logique de comptage ; commandes temps réel de GRBL 1.1 (pause, reprise, reset, annulation de jog, surcharges) ; format du rapport d'état ; licence de pyserial ; version de PySide et existence de roues pour la version de Python utilisée ; installation depuis un dépôt personnel via l'Addon Manager ; objets temporaires dans la vue 3D.

