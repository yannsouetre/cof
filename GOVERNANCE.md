# Gouvernance

- **Versionnage** : le format suit semver. `0.x` = brouillons RFC ; `1.0` sera figé quand deux implémentations indépendantes liront et écriront le format.
- **Évolutions** : toute modification normative passe par une RFC publique dans `rfcs/` (numérotée, avec une période de commentaires de 14 jours), puis une entrée dans `CHANGELOG.md`.
- **Vocabulaires** (`vocabularies/`) : versionnés séparément, en CC0 ; un fichier `.cof` déclare la version qu'il utilise.
- **Compatibilité** : un lecteur `1.x` lit tout `1.y` ; les clés inconnues sont conservées ; `extensions/` n'est jamais purgé.
- **Décisions** : mainteneur initial Yann Souetre. Engagement : transfert de la gouvernance à un groupe neutre (fondation ou consortium existant) dès que **deux adoptants indépendants** implémentent le format.
- **Conduite** : issues et RFC en français ou en anglais ; réponses sous 72 h pendant les trois premiers mois suivant le lancement.
