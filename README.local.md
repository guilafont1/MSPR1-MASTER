# Lancement local rapide

## 1) Préparer l'environnement Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Vérifier la configuration `.env`

Renseigner au minimum :
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_SSL_REQUIRED=true`
- `DB_SSL_CA_PATH=certs/aiven-ca.pem`

## 3) Lancer l'application

```bash
python app.py
```

Ouvrir : [http://localhost:5000](http://localhost:5000)

## 4) Vérifier la connexion DB

```bash
curl http://localhost:5000/health/db
```

## 5) (Optionnel) Régénérer le modèle 2027

```bash
python modele_prediction/mspr1_master.py
```

Cela met à jour :
- `modele_prediction/ridge_multiyear_2027.joblib`
- `modele_prediction/ridge_multiyear_2027_metadata.joblib`

## 6) Lancer avec Docker (alternative)

### Docker Compose (recommandé)

```bash
docker compose up --build -d
```

Ouvrir : [http://localhost:5001](http://localhost:5001)

Vérifier la DB :

```bash
curl http://localhost:5001/health/db
```

Arrêter :

```bash
docker compose down
```

### Docker classique

```bash
docker build -t mspr1-master-dashboard .
docker run --rm -d --env-file .env -p 5001:5000 --name mspr1-dashboard mspr1-master-dashboard
```

Arrêter :

```bash
docker stop mspr1-dashboard
```
