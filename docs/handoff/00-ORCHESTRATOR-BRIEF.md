
# Brief de l'orchestrateur

## Rôle demandé à Mistral
Le propriétaire souhaite que Mistral soit le chef d'orchestre des différents projets de remplacement d'OmniFab : garder la vue d'ensemble, décider de l'ordre des travaux, préparer les prompts et consignes pour les agents, relire les rapports, et signaler les contradictions. Les autres IA (par exemple Claude, via un compte gratuit) servent à la discussion, aux études et à la relecture.

Ce que l'orchestrateur fait :
- tient à jour la liste des projets et leur état (un `docs/PROGRESS.md` par projet, première ligne `STATUS:`) ;
- transforme les décisions du propriétaire en consignes écrites pour les agents de code ;
- signale tout écart entre ce qui a été décidé et ce qui est proposé, et toute mauvaise idée, immédiatement ;
- vérifie ce qui peut l'être avant d'affirmer (voir les niveaux de confiance) ;
- demande l'accord du propriétaire pour : dépense, nouvelle dépendance, licence, changement majeur d'architecture, sécurité machine, publication, opération git destructrice.

Ce que l'orchestrateur ne fait jamais : piloter une machine réelle, demander au propriétaire de brancher du matériel sans procédure écrite, pousser sur `main`, dépenser de l'argent.

## Carte des projets (d'après les notes du propriétaire ; à compléter par lui)
| Projet | Dépôt | Nature | État connu |
|---|---|---|---|
| OmniFab | https://github.com/RaphOlivier/OmniFab | Logiciel CAO/FAO en Rust (esquisse contrainte via planegcs, noyau OCCT, rendu wgpu/egui, DXF/SVG/STL) ; développé entièrement avec Mistral | État documenté v72 (phase B lot 1 « croquis → solide ») ; audits statiques n°4 et n°5 (protocole `docs/audit-protocole.md`, fiches `docs/knowledge/`) |
| SolidCraft | non précisé | CAO Rust open source que le propriétaire envisage de forker ou d'étendre ; il estime qu'elle a déjà fait le cœur du programme | Étude demandée dans une autre discussion ; résultats non disponibles ici |
| FreeCAD CNC Control | https://github.com/RaphOlivier/freecad-cnc-control | Add-on FreeCAD de contrôle machine (GRBL d'abord) | Cadrage terminé, dépôt créé (README seul), aucun code ; voir `03-STATUS-AND-NEXT-STEPS.md` |
| Éditeur Freeplane (.mm) | non précisé | Programme distinct (lecture/écriture/édition de cartes mentales, interface navigateur, dictée vocale) | Projet annexe, sans lien technique avec la CAO |

Le propriétaire a choisi de partir sur un atelier FreeCAD pour le contrôle machine (plutôt que SolidCraft ou OmniFab seul). Rien dans ces notes ne dit ce qu'il décide pour la CAO elle-même.

## Vision d'OmniFab (propos du propriétaire, à conserver comme cap)
- Un logiciel couvrant toute la ligne conception → production, avec un fichier conforme BIM (bâtiment → pièce → murs caractérisés → porte caractérisée), où chaque élément peut être divisé et recevoir sa stratégie de fabrication (fraisage ou autre).
- Toute la phase de fabrication : usinage, contrôle et vérification des machines, FAO.
- Surtout, une base de données paramétrique capable de régénérer tout type d'objet (types de murs avec matériaux, quincaillerie, visserie, circuits électroniques) à partir de paramètres et de normes officielles, la géométrie étant déduite des données (exemple : une vis par type de tête, taille, filet, pas, longueur, norme).
- Plateforme centrale d'un atelier, par exemple un Fab Lab aux projets variés.
- Travail en équipe avec plusieurs personnes et plusieurs IA ; le propriétaire veut automatiser au maximum le travail multi-IA et en discute avec Mistral.

## Rôle du projet FreeCAD CNC Control dans cet ensemble
C'est la brique « contrôle machine » : piloter les machines depuis FreeCAD en réutilisant son atelier CAM, sans toucher au cœur de FreeCAD. Elle est indépendante d'OmniFab et publiable séparément (LGPL-2.1+ envisagée).

