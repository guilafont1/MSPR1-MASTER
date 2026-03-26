# MSPR1-MASTER

Application Flask de visualisation et projection électorale (RN 2027), avec :
- ingestion de données brutes (`data_initial/`),
- alimentation MySQL (`db/schema_mysql.sql` + ETL),
- entraînement/export de modèle (`modele_prediction/mspr1_master.py`),
- dashboard web (`templates/index.html`).

## Démarrage rapide

### Local (venv)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

UI : [http://localhost:5000](http://localhost:5000)

### Docker Compose

```bash
docker compose up --build -d
```

UI : [http://localhost:5001](http://localhost:5001)

## Configuration `.env`

Variables principales :
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_SSL_REQUIRED=true`
- `DB_SSL_CA_PATH=certs/aiven-ca.pem`

Test DB :

```bash
curl http://localhost:5001/health/db
```

## Pipeline données et modèle

1. Déposer les fichiers bruts dans `data_initial/` (voir `data_initial/README.md`).
2. Créer/mettre à jour le schéma MySQL (`db/schema_mysql.sql`).
3. Charger la BDD :

```bash
python modele_prediction/etl_mspr_to_mysql.py
```

4. Entraîner/exporter le modèle Colab-like :

```bash
python modele_prediction/mspr1_master.py
```

Artefacts générés :
- `modele_prediction/ridge_multiyear_2027.joblib`
- `modele_prediction/ridge_multiyear_2027_metadata.joblib`

## Notes importantes

- L’API `/api/prediction_2027_nationale` lit uniquement les artefacts exportés (pas de fallback BDD).
- Les métriques affichées dans l’UI viennent des metadata exportées.
- Le certificat SSL Aiven est stocké dans `certs/aiven-ca.pem`.

## Analyse socio-économique (chômage / revenu)
Le tableau de bord enrichit les résultats avec des visualisations dérivées de `dataset_ml` :
- scatter : `taux_chomage` vs `score_rn` (pour une année donnée)
- scatter : `revenu_median` vs `score_rn`
- corrélations Pearson (chômage, revenu, population) avec `score_rn`

API dédiée :
- `/api/socioeco_insights?year=2022&max_points=900`

Test rapide (Docker ou local) :
```bash
curl "http://localhost:5001/api/socioeco_insights?year=2022&max_points=900"
```

## Documentation par dossier

Chaque dossier principal contient désormais un `README.md` dédié :
- `certs/`
- `dashboard/`
- `data_initial/`
- `db/`
- `Document/`
- `modele_prediction/`
- `static/`
- `templates/`
