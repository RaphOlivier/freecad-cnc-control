# Procédure manuelle n°1 — Atelier et panneau ancré (E9)

Procédure réservée au propriétaire. À lancer dans FreeCAD 1.1 stable ou 1.2
dev. **Ne pas se connecter à une machine réelle** : cette étape vérifie
uniquement le chargement de l’atelier et que le panneau n’ouvre aucun lien
série par lui-même.

## Chargement de l’atelier

1. Dans FreeCAD, ouvre **Édition → Préférences → Addon Manager → Dépôts
   personnalisés**, clique sur **+**, puis saisis l’URL du dépôt
   `https://github.com/RaphOlivier/freecad-cnc-control` et la branche `main`.
   Ouvre ensuite **Outils → Addon manager**, sélectionne **CNC Control** et
   installe le module. Aucune release, aucun tag et aucun téléchargement de
   ZIP ne sont nécessaires. Redémarre FreeCAD si le gestionnaire le demande.
   Pour reprendre une version déjà installée, utilise *Outils → Addon manager
   → Mise à jour*, puis redémarre FreeCAD. Si le bouton *Mise à jour*
   n'apparaît pas (version antérieure à `0.0.4` installée),
   désinstalle **CNC Control** puis réinstalle-le depuis le même dépôt
   personnalisé : cela ne touche pas tes documents FreeCAD.
2. Sélectionne **CNC Control** dans le sélecteur d’ateliers. Résultat attendu :
   l’icône et le libellé apparaissent, et un panneau ancré nommé
   **CNC Control** s’ouvre à droite de la vue 3D.
3. Vérifie le contenu du panneau : sélecteur de transport (Série/Socket),
   champ d’adresse et champs port/baud, boutons Connexion/Déconnexion, état
   du lien, état GRBL, position machine, version GRBL, quatre boutons temps
   réel, six boutons de jog, section **CAM job** et un journal d’événements.
   À ce stade, aucune commande n’est envoyée et aucun port n’est ouvert.

## Déplacement et ancrage

4. Prends le panneau par sa barre de titre et déplace-le vers le bord gauche,
   le bord droit, le haut, puis le bas de la fenêtre FreeCAD. Résultat attendu :
   une zone d’ancrage apparaît à chaque bord et le panneau peut s’y poser.
   Le contenu est défilable : même ancré en bas, le panneau reste petit et
   l’ascenseur permet d’atteindre tous les boutons.
5. Fais glisser le panneau au milieu de l’écran, loin des bords : il doit
   devenir une fenêtre flottante que tu peux redimensionner. Remets-le ensuite
   dans la fenêtre principale. Résultat attendu : le fond du panneau garde le
   thème de FreeCAD (pas de fond blanc), y compris lorsqu’il est mis en
   onglet avec l’arbre du modèle.
6. Ferme le panneau, puis change d’atelier et reviens à **CNC Control**.
   Résultat attendu : un seul panneau est créé et l’état du lien reste
   `disconnected`.

## Test facultatif : informations GRBL sur transport virtuel

7. Dans un terminal, place-toi à la racine du dépôt, puis lance le faux GRBL :

   ```sh
   cd "/home/raph/Documents/Projet par défaut/freecad-cnc-control"
   python tools/fake_grbl_socket.py --port 23232
   ```

   Laisse ce terminal ouvert. Résultat attendu : la ligne
   `Fake GRBL listening on 127.0.0.1:23232 (Ctrl+C to stop)` s’affiche. Ce
   script n’ouvre aucun port série et aucun périphérique réel.
8. Dans le panneau **CNC Control**, choisis **Socket** dans le sélecteur de
   transport. Le champ d’adresse s’appelle alors **Host** : saisis exactement
   `127.0.0.1`. Le champ **Port** doit valoir `23232`. Clique sur
   **Connexion**. Résultat attendu : l’état du lien passe à `connected`, la
   version GRBL affichée est `1.1h`, et la position machine se met à jour.
   Aucun mouvement n’est lancé à la connexion.
9. Clique une fois sur le bouton **X+**, puis maintiens le bouton **Y−** enfoncé
   pendant environ une seconde avant de le relâcher. Résultat attendu : le
   journal affiche une ligne `Jog X ...` pour le pas unique, plusieurs lignes
   `Jog Y ...` pendant le maintien, puis une ligne `Real-time: jog_cancel` au
   relâchement. Aucun mouvement réel n’est impliqué : le faux GRBL reçoit les
   commandes sur la boucle locale.
10. Clique sur **Déconnexion**, puis sur **Ctrl+C** dans le terminal du faux
    GRBL. Résultat attendu : l’état du lien repasse à `disconnected`,
    l’interrogation d’état s’arrête et le terminal affiche
    `Fake GRBL stopped`.

## Compte rendu

Rapporte à l’agent : version de FreeCAD, système d’exploitation, toute
traceback Python dans la vue Rapport, et la conformité de chaque résultat
attendu. Un arrêt logiciel ne remplace jamais un arrêt d’urgence matériel.
