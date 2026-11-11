
# Faits recueillis et sources

Recherches faites le 2026-11-09 et 2026-11-10 par Claude. [V] = lu dans la source citée ; [P] = probable ; [?] = non vérifié.

## FreeCAD
- Dernière version stable 1.1.3 publiée le 2026-07-25 ; la 1.1 est sortie le 2026-03-24 [V] https://wiki.freecad.org/Download et notes de version 1.1 (adresse exacte à retrouver depuis https://www.freecad.org).
- L'atelier Path est devenu CAM en 1.0. La 1.1 apporte une nouvelle bibliothèque d'outils (« Better Tool Library ») [V].
- CAM stocke les trajectoires dans un G-code interne (`Path.Command` dans des objets Path) ; les post-processeurs le convertissent vers le dialecte machine [V] https://wiki.freecad.org/CAM_scripting
- Fichiers de machine (.fcm, JSON : cinématique, limites, post-processeur recommandé) : annoncés pour « 1.2 » par Addon Academy, tandis que les préférences CAM parlent de « 26.3 » : numérotation à clarifier [V pour les deux textes, ?] https://freecad.github.io/Addon-Academy/Topics/Types/Machines
- Dépôt communautaire de machines : https://github.com/FreeCAD/Machines [V]
- Addon Manager : https://github.com/FreeCAD/AddonManager ; installe des add-ons de types Workbench, Macro, Preference Pack, Bundle, Other ; métadonnées dans `package.xml` [V].
- Dépendances Python : l'Addon Manager n'installe par pip que les paquets d'une liste autorisée ; la version lisible (marquée « avant 1.0 ») ne contient pas pyserial [V] https://github.com/FreeCAD/FreeCAD-addons/blob/master/ALLOWED_PYTHON_PACKAGES.txt. Embarquer une copie d'une bibliothèque n'est toléré que si c'est techniquement nécessaire [V] https://freecad.github.io/Addon-Academy/Topics/Dependencies/Vendoring
- Licence de FreeCAD : LGPL-2.0-or-later [V] https://snapcraft.io/freecad ; le paquet Snap fournit `freecad.cmd` (ligne de commande) [V].

## Émulateurs et logiciels existants
- Émulateurs GRBL : https://github.com/mfkiwl/grbl-sim (GRBL compilé sur PC, pseudo-terminal via socat) ; https://github.com/grblHAL/Simulator (mêmes principes, option de connexion telnet brute) [V]. Aucun des deux n'a été testé ; ils ne fonctionnent pas sous Windows via socat.
- Envoi de G-code (inspiration seulement) : Universal G-code Sender (Java), bCNC (Python, GPLv2), CNCjs (MIT), Candle (GPLv3), GRBL-Plotter (GPLv3) ; GRBL lui-même GPLv3 [V, page de comparaison du wiki de Universal G-code Sender https://github.com/winder/Universal-G-Code-Sender/wiki, à reconfirmer dans chaque dépôt].
- LinuxCNC : module Python `linuxcnc` (état, commandes, erreurs, lecture INI) [V] https://linuxcnc.org/docs/2.8/html/config/python-interface.html ; Axis : GPL v2+ [V, en-tête de source].

## Outils IA et GitHub (faits datés)
- Claude Code : se connecte avec un forfait Pro, Max ou Ultra, ou avec une clé API (message d'erreur affiché au propriétaire le 2026-11-09). Permissions et règles d'interdiction : https://code.claude.com/docs/en/permissions [V] ; mode non interactif : https://docs.claude.com/en/docs/claude-code/headless [V].
- Connecteur GitHub de Claude : en lecture seule (fichiers, branches, métadonnées ; ni historique de commits, ni demandes de fusion, ni tickets) [V] https://claude.com/docs/connectors/github
- Mistral Vibe : le programme en ligne de commande est ouvert ; inclus dans les abonnements payants Le Chat Pro et Team ; le modèle Devstral 2 est passé en API payante sauf sur le plan « Experiment » de Mistral Studio, annoncé gratuit pour tester et prototyper, d'après l'annonce du 27 janvier 2026 [V, datée] https://mistral.ai/en/news/mistral-vibe-2-0/ ; installation : https://docs.mistral.ai/vibe.md [V]. Limites actuelles du plan gratuit : [?].
- GitHub Codespaces : 120 heures-cœur et 15 Go par mois pour un compte personnel gratuit ; arrêt après 30 minutes d'inactivité par défaut ; pas de facturation si aucun moyen de paiement n'est enregistré [V] https://docs.github.com/en/billing/concepts/product-billing/github-codespaces et https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage
- GitHub Actions : 2 000 minutes par mois pour un compte gratuit (page ancienne, à reconfirmer) ; machines standard gratuites sur un dépôt public [P] https://docs.github.com/en/get-started/learning-about-github/githubs-products
- Environnement de Claude (conversation) : peut cloner un dépôt public [V, testé le 2026-11-10], ne peut pas écrire dans un dépôt ; l'interface de suivi des exécutions de GitHub a répondu par une erreur 403 [V].

## GRBL 1.1 (tout à vérifier dans la documentation avant d'implémenter)
Documentation à consulter : https://github.com/gnea/grbl/wiki (GRBL 1.1). Points à confirmer : taille du tampon de réception et comptage de caractères [?], commandes temps réel (état, pause, reprise, reset, annulation de jog, surcharges) [?], format du rapport d'état [?], mode de vérification `$C` [?], palpage G38.2 [P], décalages G10 L20 [?], mode laser [P].

