# Dashboard MSPR — Version 1

Dashboard minimal pour la gestion des évaluations et grilles MSPR (évaluations individuelles Coach, grilles Bloc 3 I1 EISI, règles de validation, sujets). Interface épurée, template moderne, 100 % Python.

## Prérequis

- Python 3.10+
- Ou Docker et Docker Compose

## Lancer en local (sans Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
python app.py
```

Ouvrir [http://localhost:5000](http://localhost:5000).

### Configuration BDD MySQL (SSL)

1. Copier la base d'environnement :

```bash
copy .env.example .env
```

2. Mettre à jour `DB_PASSWORD` dans `.env`.
3. Le certificat CA est déjà fourni dans `certs/aiven-ca.pem`.
4. Installer les dépendances puis lancer l'app :

```bash
pip install -r requirements.txt
python app.py
```

5. Vérifier la connexion BDD :

```bash
curl http://localhost:5000/health/db
```

## Lancer avec Docker

```bash
docker build -t mspr-dashboard .
docker run --rm -d -p 5001:5000 mspr-dashboard
echo "Dashboard : http://localhost:5001"
```

Le conteneur tourne en arrière-plan. Pour l’arrêter : `docker stop $(docker ps -q --filter ancestor=mspr-dashboard)`.

Ou avec Docker Compose :

```bash
docker compose up --build
```

Puis [http://localhost:5001](http://localhost:5001).

## Structure

- `app.py` — Application Flask (routes)
- `templates/` — Pages HTML (Jinja2)
- `static/css/style.css` — Styles (thème sombre, responsive)
- `Document/` — Documents de référence (grilles, règles, sujets) — non servis par l’app

## Pages

| Route           | Description                          |
|----------------|--------------------------------------|
| `/`            | Accueil, liens vers les sections     |
| `/evaluations` | Évaluations individuelles Coach     |
| `/grilles`     | Grilles MSPR (Bloc 3, I1 EISI)       |
| `/regles`      | Règles de validation MSPR            |
| `/sujets`      | Sujets MSPR (Bloc 3, I1 EISI)        |

## Évolutions possibles (après v1)

- Intégration des PDF/ODT (affichage ou liens de téléchargement)
- Authentification (coachs / apprenants)
- Saisie et suivi des évaluations
- Export des grilles

## Licence

Usage interne / projet MSPR.
