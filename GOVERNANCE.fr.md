# Gouvernance

*(English: [GOVERNANCE.md](GOVERNANCE.md))*

- **Versionnage** : semver. Un lecteur `1.x` lit tout fichier `1.y` ; les versions mineures suivantes n'ajoutent que des champs optionnels ; les clés inconnues sont conservées et `extensions` n'est jamais purgé.
- **Évolutions du format** : toute modification passe par une RFC publique dans `rfcs/` (numérotée, période de commentaires de 14 jours), puis une entrée dans `CHANGELOG.md`. Les corrections de bugs des outils de référence n'ont pas besoin de RFC.
- **Vocabulaires** (`vocabularies/`) : versionnés séparément, publiés en CC0.
- **Décisions** : mainteneur initial Yann Souetre. Engagement : transfert de la gouvernance à un organe neutre (fondation ou consortium existant) dès que **deux adoptants indépendants** implémentent le format.
- **Neutralité** : la galerie et les outils du projet n'ont jamais de privilège dans le format ; l'API de catalogue est ouverte, les autres galeries et boutiques sont bienvenues, le badge « compatible COF » est gratuit.
- **Conduite** : issues et RFC en français ou en anglais ; réponses sous 72 h pendant les trois mois suivant le lancement.
