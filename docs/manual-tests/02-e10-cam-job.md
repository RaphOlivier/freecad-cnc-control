# Procédure manuelle n°2 — Envoi du Job CAM sélectionné (E10)

Procédure réservée au propriétaire. **Aucune machine réelle ne doit être
connectée.** Le seul contrôleur autorisé ici est le faux GRBL local fourni avec
le dépôt. Un arrêt logiciel ne remplace jamais un arrêt d’urgence matériel.

## Préparation

1. Dans FreeCAD, crée une pièce très simple (par exemple un carré de 40 × 40 mm)
   et un Job CAM avec une seule opération peu profonde. Le but est d’avoir un
   Job fabriqué, pas d’usiner quelque chose.
2. Depuis la racine du dépôt, lance le faux GRBL sur une boucle locale :
   `python tools/fake_grbl_socket.py --port 23232`. Laisse cette fenêtre ouverte.
3. Dans le panneau **CNC Control**, choisis **Socket**, saisis `127.0.0.1` et
   `23232`, puis clique sur **Connexion**. Résultat attendu : l’état du lien
   passe à `connected`, la version affichée est `1.1h`, et la position machine
   apparaît. Aucun mouvement n’est lancé à la connexion.

## Envoi du Job

4. Sélectionne le **Job** dans l’arbre du document (pas seulement une
   opération), puis clique sur **Envoyer le Job CAM sélectionné** dans le
   panneau, ou sur *CNC → Send selected CAM Job* dans le menu de l’atelier.
5. Résultat attendu : une boîte de confirmation affiche le nom de l’opération,
   le nombre de lignes et les avertissements éventuels. Clique d’abord sur
   **Annuler** : aucun précontrôle n’est envoyé au faux GRBL et le journal
   affiche `CAM job cancelled`.
6. Reclique sur le bouton d’envoi et accepte la confirmation. Résultat attendu :
   le journal affiche un événement `preflight` accepté avec le nom de
   l’opération. Si le précontrôle refuse le programme, aucune ligne n’est
   streamée et les raisons s’affichent.
7. Choisis **Oui** pour le mode de vérification GRBL (`$C`). Résultat attendu :
   le journal affiche `check_mode enabled`, puis `Stream: ... completed True`,
   puis `check_mode disabled`. Le faux GRBL n’exécute aucun mouvement réel.
8. Facultatif : répète l’envoi en choisissant **Non** au mode de vérification,
   puis **Annuler** à la question suivante. Résultat attendu : aucun stream.
9. Déconnecte-toi du faux GRBL et arrête le script avec **Ctrl+C**. Vérifie que
   l’état du lien repasse à `disconnected` et que l’interrogation d’état s’arrête.

## Compte rendu

Rapporte à l’agent : version de FreeCAD, système d’exploitation, toute traceback
Python dans la vue Rapport, et la conformité de chaque résultat attendu. Si une
opération est ignorée, indique son nom : les tests automatisés couvrent déjà le
cas des codes refusés par le précontrôle.
