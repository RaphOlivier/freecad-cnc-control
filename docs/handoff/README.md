
# Dossier de passation pour l'orchestrateur (Mistral)

Rédigé par Claude (Anthropic) le 2026-11-10, à partir de la discussion de cadrage du 2026-11-09 et des notes que Claude conserve sur le propriétaire. Langue : français (exception à la règle « documentation du dépôt en anglais », car ce sont des documents de pilotage pour le propriétaire et son orchestrateur).

Légende de confiance utilisée partout : **[V]** vérifié (source citée), **[P]** probable, **[?]** à vérifier. Ce qui n'est pas marqué est une décision du propriétaire.

## Ordre de lecture
1. `00-ORCHESTRATOR-BRIEF.md` : le rôle d'orchestrateur et la carte des projets de remplacement d'OmniFab.
2. `01-OWNER-AND-WORKING-RULES.md` : qui est le propriétaire, comment lui parler, contraintes.
3. `02-FREECAD-CNC-CONTROL.md` : ce qu'est le projet FreeCAD CNC Control (résumé).
4. `03-STATUS-AND-NEXT-STEPS.md` : ce qui est fait, ce qui reste, par quoi commencer.
5. `04-RESEARCH-FINDINGS.md` : faits vérifiés et sources.
6. `05-TOOLS-AND-WORKFLOWS.md` : outils IA et GitHub, ce qui est possible gratuitement.
7. `06-OPEN-QUESTIONS.md` : questions ouvertes et vérifications à faire.

Documents de référence du projet (à la racine et dans `docs/`) :
- `../FRAMING.md` : dossier de cadrage complet (spécification, 28 décisions, hypothèses, étude de l'existant FreeCAD, licences, risques).
- `../../AGENTS.md` : règles pour les agents de code (architecture, sécurité, tests, méthode). `../../CLAUDE.md` y renvoie.
- `../LAUNCH_PROMPT.md` : prompt de lancement avec le plan E0 à E16.
- `../PROGRESS.md` : état d'avancement (première ligne `STATUS:` lisible par les scripts et les relais).

## Ce qui n'existe pas encore
Aucun code n'est écrit. Il n'y a pas d'autres fichiers de code à transmettre : le plan d'implémentation est dans `../LAUNCH_PROMPT.md`.

## Limites de ce dossier
Claude n'a pas accès aux autres discussions du propriétaire (audits d'OmniFab n°4 et n°5, étude de SolidCraft, organisation multi-IA). Seules des notes très courtes en subsistent (voir `00-ORCHESTRATOR-BRIEF.md`). Le propriétaire peut coller ces rapports dans un dossier `docs/handoff/external/` pour les compléter.

