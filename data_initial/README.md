# Données brutes (CSV)

Ce dossier est prévu pour déposer les fichiers CSV bruts (non transformés) avant ingestion dans l'application.

Recommandations :
- Utiliser des noms de fichiers explicites (ex: `indicateurs_communes_brut.csv`).
- Garder ces CSV "source of truth" : ne pas les modifier après ingestion.
- Les fichiers traités/transformés peuvent aller dans un autre dossier (ex: `data/processed/`) lors des prochaines étapes.

Structure attendue pour l’ETL actuel (`modele_prediction/etl_mspr_to_mysql.py`) :
- `data-presidentielle/` : `resultats-presidentielle-2002.xls`, `...-2007.xls`, `...-2012.xls`, `...-2017.csv`, `...-2022.xlsx`
- `population-par-commune-INSEE/` : `donnees_communes.csv`
- `revenu-des-francais-a-la-commune-2021/` : `revenu_des_francais_a_la_commune_2021.csv`
- `Taux-de-chomage/` : `taux-de-chomage.xlsx`

