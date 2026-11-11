
Tu es l'agent de développement de l'add-on FreeCAD « CNC Control » (nom provisoire). Lis d'abord AGENTS.md à la racine du dépôt, puis docs/handoff/README.md, docs/FRAMING.md et docs/PROGRESS.md. Je parle français avec toi ; le code, les commentaires, les commits et la documentation du dépôt sont en anglais.

## Mission
Réaliser le jalon 1 : un atelier FreeCAD « CNC Control » avec panneau ancré, pilotant du GRBL 1.1 par liaison série, installable via l'Addon Manager depuis un dépôt Git. Fonctions : connexion, état/position, ordres temps réel, jog (pas fixes et continu), streaming par comptage de caractères, alarmes, $H, $X, lecture de $$, décalages (G54… et G92), surcharges de vitesse, macros, sonde (Z puis bords X/Y), envoi d'un fichier G-code ou du Job CAM sélectionné via notre post-processeur GRBL, marqueur 3D et avancement du trajet (objets temporaires), contrôles avant job, pause automatique sur perte de liaison, journal série.

## Critères de réussite vérifiables
1. `pytest tests/core tests/worker` passe sur Linux, Windows et macOS en intégration continue.
2. `QT_QPA_PLATFORM=offscreen pytest tests/gui` passe.
3. `pytest -m integration tests/integration` passe sous Linux (simulateur GRBL compilé).
4. Un test automatique fait tourner un job complet de bout en bout contre le faux GRBL : connexion, vérification des limites, mode de vérification, job réel avec streaming, pause/reprise, alarme provoquée (arrêt sans reprise automatique), fin de job.
5. Un test coupe la liaison pendant un job : pause automatique, reprise seulement après reconnexion et confirmation.
6. Un test coupe le signal de vie de l'interface : le processus série met la machine en pause.
7. Le paquet est installable via l'Addon Manager (procédure manuelle documentée, lancée par moi).
8. `REPORT.md` rédigé, `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/OPEN_QUESTIONS.md` à jour.

## Règles de sécurité (absolues)
Ne te connecte jamais à une machine réelle ni à un port série réel. Tests et outils : transports virtuels uniquement (mémoire, socket, pseudo-terminal, émulateur). Tout essai sur matériel est une procédure dans docs/manual-tests/ que je lance moi-même. Aucun mouvement sans action explicite de l'utilisateur ; ordres temps réel jamais bloqués par la file de streaming.

## Plan en étapes courtes (chacune avec son test ; un commit par étape testée)
E0. Squelette du dépôt, CI sur 3 systèmes, licence LGPL-2.1+ provisoire, package.xml provisoire. Test : la CI passe sur un test vide.
E1. Inspection de l'API FreeCAD installée (lecture seule, ligne de commande) : post-processeurs, objets temporaires, Qt, structure d'un atelier ; consigner dans docs/DECISIONS.md (vérifié/probable/à vérifier). Test : note de décisions complète.
E2. Protocole GRBL dans core/ : analyse des réponses (ok, erreurs, alarmes, rapport d'état, messages). Test : cas de la documentation GRBL 1.1 ; vérifier la documentation, ne pas deviner.
E3. Faux GRBL Python et transports de test (mémoire, socket, pseudo-terminal Linux/macOS). Test : conversation de base.
E4. Streamer par comptage de caractères avec ordres temps réel prioritaires. Test : débit, arrêt sur alarme, aucune reprise automatique.
E5. Interface « contrôleur » + implémentation GRBL (état, jog, capacités). Test : contre le faux GRBL.
E6. Processus série séparé, protocole JSON, battement de vie, pause automatique. Test : coupure de l'interface et de la liaison. Point d'étape : la communication est utilisable sans FreeCAD.
E7. Analyse du G-code : limites, trajet, correspondance ligne-segment, noms d'opérations. Test : fichiers fabriqués à la main.
E8. Contrôles avant job : refus hors limites, confirmation, mode de vérification, simulateur. Test : cas limites.
E9. Couche d'adaptation FreeCAD (1.1 et 1.2 dev), atelier, panneau ancré (connexion, état, jog). Test : Qt hors-écran, API simulée d'après E1. Procédure manuelle n°1 : je lance, je te rapporte.
E10. Post-processeur GRBL propre avec commentaires d'opération et envoi du Job sélectionné. Test : sortie sur Jobs fabriqués. Procédure manuelle n°2.
E11. Marqueur et avancement en objets temporaires. Test : logique sur le G-code ; procédure manuelle n°3.
E12. $H, $X, $$ en lecture, décalages G54… et G92, mise à zéro. Test : faux GRBL.
E13. Surcharges de vitesse (sacrifiable en dernier).
E14. Macros avec confirmation avant mouvement (sacrifiable en deuxième).
E15. Sonde : Z puis bords X/Y, confirmation avant chaque cycle (sacrifiable en premier).
E16. Journal série tournant, packaging pour l'Addon Manager, test de bout en bout du critère 4, REPORT.md. Procédure manuelle n°4 : installation depuis le dépôt.
Si le calendrier glisse, abandonne dans l'ordre : E15, E14, E13, en le notant dans REPORT.md.

## Ce que tu décides seul
Choix internes de conception, nommage, structure des tests, découpage en commits, hypothèses documentées dans docs/DECISIONS.md (avec confiance vérifié/probable/à vérifier).

## Ce qui exige mon accord préalable
Nouvelle dépendance, décision de licence, changement majeur d'architecture, tout ce qui touche à la sécurité machine, publication, opérations git destructrices, réutilisation de code tiers. Pose la question dans docs/OPEN_QUESTIONS.md, passe à une autre étape, et signale-le dans ton prochain message.

## Conditions d'arrêt
Arrête-toi après 3 échecs sur une même étape, à la limite d'usage, ou quand tu as besoin de mon accord sans autre étape possible. À chaque fin de session, mets à jour la première ligne de docs/PROGRESS.md (STATUS: …) comme décrit dans AGENTS.md section 10, et laisse docs/PROGRESS.md dans un état qui permet à un autre agent de reprendre sans rien me demander d'essentiel.

## Git
Branche de travail dédiée ; un commit par petite étape testée ; push seulement sur cette branche ; jamais de force-push ni de modification de main ; je fusionne.

## Après le jalon 1
Écris REPORT.md (réalisé, testé, points ouverts, procédures manuelles à lancer, risques) et un résumé court ici. Enchaîne ensuite sur le jalon suivant (liaison RS-232 avec détection des paramètres : commandes inoffensives uniquement, jamais de mouvement, ma confirmation obligatoire ; tests sur ports virtuels uniquement ; l'essai réel est une procédure manuelle pour moi), avec les mêmes règles de sécurité, d'accord préalable et d'arrêt, sauf instruction contraire de ma part ou de l'orchestrateur. Écris d'abord le plan de ce jalon dans docs/ avant de coder.

## Rapport attendu
Un message final : ce qui est fait, les tests passés, les écarts au plan, les points ouverts, les procédures manuelles à lancer, les risques.

