# `modele_prediction/`

Scripts de préparation, entraînement et export des modèles.

## Fichiers principaux

- `etl_mspr_to_mysql.py` : ETL des données brutes vers MySQL.
- `mspr1_master.py` : pipeline de référence (préparation, entraînement, projection 2027, export artefacts).
- `linear_regression_model.joblib` : ancien modèle historique.
- `ridge_multiyear_2027.joblib` : modèle Ridge exporté.
- `ridge_multiyear_2027_metadata.joblib` : métriques et méta-infos du modèle exporté.
- `outputs/` : fichiers intermédiaires générés (CSV de travail).

## Commandes utiles

```bash
python modele_prediction/etl_mspr_to_mysql.py
python modele_prediction/mspr1_master.py
```

## Important

L’API de projection 2027 lit les artefacts Ridge exportés de ce dossier.
