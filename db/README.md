# `db/`

Scripts SQL de structure de base de données.

## Contenu

- `schema_mysql.sql` : création du schéma MSPR (`staging`, `DWH`, `dataset_ml`).

## Usage

Appliquer le script sur la base cible avant l’ETL, puis relancer l’ingestion :

```bash
python modele_prediction/etl_mspr_to_mysql.py
```

Le script ETL s’attend à trouver les tables et contraintes définies ici.
