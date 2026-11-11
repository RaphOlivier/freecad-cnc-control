
# Outils et façons de travailler (sans payer)

## Situation
- Claude (gratuit) : discussion, études, rédaction ; peut écrire du code et lancer des tests dans son environnement, remettre des fichiers au propriétaire ; ne peut pas pousser sur GitHub ni travailler sans sollicitation ; limité par les quotas du forfait gratuit. Claude Code est exclu (payant).
- Mistral (gratuit) : outil principal d'OmniFab ; le propriétaire l'utilise dans le navigateur (Mistral Vibe / Le Chat) et colle les commandes dans son terminal. L'agent en ligne de commande Vibe est utilisable avec une clé du plan Experiment, sous réserve des limites actuelles [?].
- GitHub (gratuit) : dépôt public, Actions pour les tests (3 systèmes), Codespaces possible (120 h-cœur/mois).

## Modes de travail possibles
**Mode A, conversation + commandes collées (pratique actuelle pour OmniFab).** L'orchestrateur écrit les fichiers et les commandes ; le propriétaire les colle dans Konsole ; GitHub Actions lance les tests ; le propriétaire rapporte les erreurs. Avantages : aucun outil à installer, gratuit ; inconvénient : beaucoup de copier-coller et pas d'exécution autonome.
**Mode B, agent en ligne de commande (Mistral Vibe CLI).** L'agent lit `AGENTS.md`, modifie les fichiers et lance les tests avec l'approbation du propriétaire (agent `accept-edits` pour approuver seulement les modifications de fichiers [V]). Vérifier d'abord les limites du plan gratuit [?]. Je n'ai pas vérifié l'existence d'un mode non interactif sûr avec règles d'interdiction : ne pas lancer en boucle sans surveillance.
**Mode C, GitHub Codespaces.** Un ordinateur Linux dans le nuage rattaché au dépôt : aucune machine CNC n'y est branchable (garantie de sécurité), environnement identique à chaque fois ; mais arrêt après 30 minutes d'inactivité et quota de 60 heures par mois sur une petite machine. À envisager comme lieu de travail du Mode B.

## Relais entre IA (règle commune)
Un seul agent à la fois sur un même dépôt. Avant de changer d'agent : mettre à jour `docs/PROGRESS.md` (première ligne `STATUS:`), faire un commit et un push de la branche de travail ; l'agent suivant lit `AGENTS.md` puis `docs/PROGRESS.md`.

## Intégration continue (déjà décidée)
GitHub Actions sur Linux, Windows et macOS pour le cœur, le processus série et les tests Qt hors-écran ; simulateur compilé sous Linux uniquement. Les machines standard sont gratuites sur un dépôt public [P].

## Deux idées étudiées et écartées
- Boucle automatique avec Claude Code (script `run_agent.sh`, règles `.claude/settings.json`) : abandonnée, Claude Code étant payant.
- Écriture directe sur GitHub par un connecteur : le connecteur officiel de Claude est en lecture seule [V] ; un connecteur d'écriture demanderait un serveur hébergé et un jeton d'accès, ce qui est déconseillé à un débutant.

