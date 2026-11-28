# Procédure manuelle n°1 — Atelier et panneau ancré (E9)

Procédure réservée au propriétaire. À lancer dans FreeCAD 1.1 stable ou 1.2
dev. **Ne pas se connecter à une machine réelle** : cette étape vérifie
uniquement le chargement de l’atelier et que le panneau n’ouvre aucun lien
série par lui-même.

1. Dans FreeCAD, ouvre **Édition → Préférences → Addon Manager → Dépôts
   personnalisés**, clique sur **+**, puis saisis l’URL du dépôt
   `https://github.com/RaphOlivier/freecad-cnc-control` et la branche `main`.
   Ouvre ensuite **Outils → Addon manager**, sélectionne **CNC Control** et
   installe le module. Aucune release, aucun tag et aucun téléchargement de
   ZIP ne sont nécessaires. Redémarre FreeCAD si le gestionnaire le demande.
2. Sélectionne **CNC Control** dans le sélecteur d’ateliers. Résultat attendu :
   l’icône et le libellé apparaissent, et un panneau ancré nommé
   **CNC Control** s’ouvre à droite de la vue 3D.
3. Vérifie le contenu du panneau : sélecteur de transport (Série/Socket),
   champ d’adresse et champs port/baud, boutons Connexion/Déconnexion, état
   du lien, état GRBL, position machine, version GRBL, quatre boutons temps
   réel, six boutons de jog et un journal d’événements. À ce stade, aucune
   commande n’est envoyée et aucun port n’est ouvert.
4. Déplace le panneau sur un autre bord, ferme-le, puis change d’atelier et
   reviens. Résultat attendu : aucun panneau en double et l’état du lien
   reste `disconnected`.
5. Facultatif (transport virtuel uniquement) : lance un faux GRBL sur un port
   TCP local, sélectionne **Socket**, saisis `127.0.0.1` et ce port, puis
   appuie sur **Connexion**. Résultat attendu : un événement `connected` avec
   `1.1h`, l’interrogation d’état met à jour la position machine, les boutons
   de jog ajoutent des lignes `Jog ...` au journal, et le relâchement d’un
   bouton de jog maintenu ajoute une commande temps réel d’annulation de jog.
6. Appuie sur **Déconnexion**. Résultat attendu : l’état repasse à
   `disconnected` et l’interrogation d’état s’arrête.

Rapporte à l’agent : version de FreeCAD, système d’exploitation, toute
traceback Python dans la vue Rapport, et la conformité de chaque résultat
attendu. Un arrêt logiciel ne remplace jamais un arrêt d’urgence matériel.
