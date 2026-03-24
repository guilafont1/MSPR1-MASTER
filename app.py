"""
Dashboard MSPR - Version 1
Application Flask pour le tableau de bord de prédiction électorale nationale.
"""
import os
import warnings
import numpy as np
import pandas as pd
import joblib
from dotenv import load_dotenv
import mysql.connector
from flask import Flask, render_template, request, jsonify

load_dotenv()  # Charge automatiquement les variables depuis `.env` (utile en local)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# Chargement du modèle au démarrage
MODEL_PATH = os.path.join(os.path.dirname(__file__), "modele_prediction", "linear_regression_model.joblib")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    model = joblib.load(MODEL_PATH)


@app.route("/")
def index():
    """Page d'accueil du dashboard."""
    return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Endpoint de prédiction.
    Attend un JSON : { "score_2017": float, "delta": float }
    Retourne       : { "prediction": float, "features": {...} }
    """
    data = request.get_json(force=True)
    try:
        score_2017 = float(data["score_2017"])
        delta      = float(data["delta"])
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Paramètres invalides : {e}"}), 400

    X = pd.DataFrame([[score_2017, delta]], columns=["2017", "delta"])
    prediction = float(model.predict(X)[0])

    return jsonify({
        "prediction": round(prediction, 4),
        "features": {
            "score_2017": score_2017,
            "delta": delta,
        },
        "model_info": {
            "type": "LinearRegression",
            "coef": {
                "2017": round(float(model.coef_[0]), 5),
                "delta": round(float(model.coef_[1]), 5),
            },
            "intercept": round(float(model.intercept_), 5),
        },
    })


@app.route("/api/model_info", methods=["GET"])
def model_info():
    """Retourne les métadonnées du modèle chargé."""
    return jsonify({
        "type": "LinearRegression",
        "features": list(model.feature_names_in_),
        "coef": {
            str(f): round(float(c), 5)
            for f, c in zip(model.feature_names_in_, model.coef_)
        },
        "intercept": round(float(model.intercept_), 5),
        "n_features": int(model.n_features_in_),
    })


@app.route("/api/predict_range", methods=["GET"])
def predict_range():
    """
    Génère des prédictions pour un éventail de scores 2017 (0.05 → 0.80).
    Paramètre optionnel : delta (défaut 0.0)
    Retourne : { labels: [...], predictions: [...] }
    """
    delta = float(request.args.get("delta", 0.0))
    scores = np.round(np.arange(0.05, 0.81, 0.05), 4).tolist()
    X = pd.DataFrame([[s, delta] for s in scores], columns=["2017", "delta"])
    preds = [round(float(v), 4) for v in model.predict(X)]
    return jsonify({"labels": scores, "predictions": preds, "delta": delta})


@app.route("/api/sensitivity", methods=["GET"])
def sensitivity():
    """
    Analyse de sensibilité : impact du delta sur la prédiction pour
    3 profils de score 2017 (bas=0.15, moyen=0.30, haut=0.45).
    Retourne des courbes delta vs prediction pour chaque profil.
    """
    deltas = np.round(np.arange(-0.20, 0.21, 0.02), 4).tolist()
    profiles = {"Profil bas (15%)\u202f": 0.15, "Profil moyen (30%)\u202f": 0.30, "Profil haut (45%)\u202f": 0.45}
    result = {"labels": deltas, "series": {}}
    for name, score in profiles.items():
        X = pd.DataFrame([[score, d] for d in deltas], columns=["2017", "delta"])
        result["series"][name] = [round(float(v), 4) for v in model.predict(X)]
    return jsonify(result)


def get_db_config():
    """Construit la configuration MySQL depuis les variables d'environnement."""
    return {
        "host": os.environ.get("DB_HOST"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_NAME"),
        "ssl_disabled": os.environ.get("DB_SSL_REQUIRED", "true").lower() != "true",
        "ssl_ca": os.environ.get("DB_SSL_CA_PATH"),
        "connection_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5")),
    }


@app.route("/health/db", methods=["GET"])
def db_health():
    """Vérifie la connectivité à la base MySQL distante."""
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        connection.close()
        return jsonify({"status": "ok", "message": "Connexion MySQL opérationnelle"}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Connexion MySQL impossible: {exc.msg}"}), 500


@app.route("/api/data_health", methods=["GET"])
def data_health():
    """
    Renvoie un score "Data Health" dérivé de `dataset_ml` pour alimenter le radar front.
    Les scores sont normalisés entre 0 et 100.
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        dataset_count = 0
        cursor.execute("SELECT COUNT(*) FROM dataset_ml")
        dataset_count = cursor.fetchone()[0]

        # Complétude / validation par colonnes (null sums)
        cursor.execute(
            """
            SELECT
              SUM(score_rn IS NULL),
              SUM(revenu_median IS NULL),
              SUM(population IS NULL),
              SUM(taux_chomage IS NULL)
            FROM dataset_ml
            """
        )
        null_score_rn, null_revenu, null_pop, null_chom = cursor.fetchone()

        expected_years = [2002, 2007, 2012, 2017, 2022]
        cursor.execute(
            f"""
            SELECT annee, COUNT(*) 
            FROM dataset_ml 
            WHERE annee IN ({",".join(["%s"] * len(expected_years))})
            GROUP BY annee
            """,
            tuple(expected_years),
        )
        year_counts = cursor.fetchall()  # (annee, count)
        years_present = sorted([int(y) for (y, c) in year_counts if int(c) > 0])
        temporal_coverage = (len(years_present) / float(len(expected_years))) * 100.0 if expected_years else 0.0

        freshness = 0.0
        if years_present:
            freshness = (max(years_present) - min(years_present)) / (max(expected_years) - min(expected_years)) * 100.0
            freshness = max(0.0, min(100.0, float(freshness)))

        # Score de complétude basé sur null de score_rn
        if dataset_count and int(null_score_rn) == 0:
            completeness = 100.0
        else:
            completeness = max(0.0, min(100.0, (1.0 - (float(null_score_rn) / float(dataset_count or 1))) * 100.0))

        # Traçabilité : combien des 4 composantes sont non-NULL sur dataset_ml
        validated = 0
        if int(null_score_rn) == 0:
            validated += 1
        if int(null_revenu) == 0:
            validated += 1
        if int(null_pop) == 0:
            validated += 1
        if int(null_chom) == 0:
            validated += 1
        sources_validated_pct = (validated / 4.0) * 100.0

        # Exactitude : R2 du modèle sur (2012,2017)->2022
        years = (2012, 2017, 2022)
        cursor.execute(
            "SELECT codgeo, annee, score_rn FROM dataset_ml WHERE annee IN (%s,%s,%s)",
            years,
        )
        rows = cursor.fetchall()

        if not rows:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "dataset_ml vide"}), 500

        df = pd.DataFrame(rows, columns=["codgeo", "annee", "score_rn"])
        wide = df.pivot_table(index="codgeo", columns="annee", values="score_rn", aggfunc="first")
        if not all(y in wide.columns for y in years):
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "Années manquantes pour le calcul R2"}), 500

        wide["delta"] = wide[2017] - wide[2012]
        wide = wide.dropna(subset=[2012, 2017, 2022, "delta"])

        X = wide[[2017, "delta"]].copy()
        X.columns = ["2017", "delta"]
        y_true = wide[2022].astype(float).values
        y_pred = model.predict(X)

        y_mean = float(y_true.mean())
        ss_tot = float(((y_true - y_mean) ** 2).sum())
        ss_res = float(((y_true - y_pred) ** 2).sum())
        r2 = 0.0 if ss_tot == 0.0 else (1.0 - ss_res / ss_tot)
        exactitude = max(0.0, min(100.0, float(r2) * 100.0))

        # Cohérence = couverture temporelle (proxy)
        coherence = max(0.0, min(100.0, float(temporal_coverage)))

        # Accessibilité : taille dataset et présence d'années-clés
        accessibility = 100.0 if dataset_count and int(dataset_count) > 1000 else 60.0

        cursor.close()
        connection.close()

        labels = ["Complétude", "Cohérence", "Fraîcheur", "Traçabilité", "Exactitude", "Accessibilité"]
        values = [
            round(float(completeness), 1),
            round(float(coherence), 1),
            round(float(freshness), 1),
            round(float(sources_validated_pct), 1),
            round(float(exactitude), 1),
            round(float(accessibility), 1),
        ]

        cards = {
            "data_cleaned_pct": values[0],
            "missing_handled_pct": values[0],
            "temporal_coverage_pct": values[1],
            "sources_validated_text": f"{validated} / 4",
        }

        return jsonify({"status": "ok", "labels": labels, "values": values, "cards": cards}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/model_metrics", methods=["GET"])
def model_metrics():
    """
    KPI modèle calculés directement à partir de `dataset_ml` :
    - R² (sur reconstruction 2012/2017 -> prédiction 2022 via model sklearn)
    - MSE, RMSE, MAE
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    # On veut coller à la logique de `mspr1_master.py` :
    # - df_ml = df_wide.dropna(subset=[2002,2007,2012,2017,2022])
    # - features simplifiées : X = [2017, delta], delta = score_2017 - score_2012
    # - évaluation : train_test_split(test_size=0.2, random_state=42)
    try:
        from sklearn.model_selection import train_test_split

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        years_all = (2002, 2007, 2012, 2017, 2022)
        cursor.execute(
            f"""
            SELECT codgeo, annee, score_rn
            FROM dataset_ml
            WHERE annee IN ({",".join(["%s"] * len(years_all))})
            """,
            years_all,
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        if not rows:
            return jsonify({"status": "error", "message": "dataset_ml vide"}), 500

        df = pd.DataFrame(rows, columns=["codgeo", "annee", "score_rn"])
        wide = df.pivot_table(index="codgeo", columns="annee", values="score_rn", aggfunc="first")

        if not all(y in wide.columns for y in years_all):
            return jsonify({"status": "error", "message": "Années manquantes pour KPI modèle"}), 500

        wide["delta"] = wide[2017] - wide[2012]
        # cohérent avec mspr1_master.py (dropna sur 5 années)
        wide = wide.dropna(subset=[2002, 2007, 2012, 2017, 2022, "delta"])
        n_samples = int(len(wide))
        if n_samples == 0:
            return jsonify({"status": "error", "message": "Aucun échantillon valide après dropna"}), 500

        X = wide[[2017, "delta"]].copy()
        X.columns = ["2017", "delta"]
        y_true = wide[2022].astype(float).values

        # Métriques "full dataset" (utile en soutenance)
        y_pred_full = model.predict(X)
        mse_full = float(((y_true - y_pred_full) ** 2).mean())
        rmse_full = float(mse_full ** 0.5)
        mae_full = float(abs(y_true - y_pred_full).mean())
        y_mean = float(y_true.mean())
        ss_tot = float(((y_true - y_mean) ** 2).sum())
        ss_res = float(((y_true - y_pred_full) ** 2).sum())
        r2_full = 0.0 if ss_tot == 0.0 else (1.0 - ss_res / ss_tot)

        # Métriques "test split" pour coller aux captures Colab
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_true, test_size=0.2, random_state=42
        )
        y_pred_test = model.predict(X_test)
        mse_test = float(((y_test - y_pred_test) ** 2).mean())
        rmse_test = float(mse_test ** 0.5)
        mae_test = float(abs(y_test - y_pred_test).mean())
        residuals_test = (y_test - y_pred_test).astype(float)
        residuals_test_pts = residuals_test * 100.0  # conversion en "points" (0..1 => 0..100)

        # Histogramme compact pour visualisation front (Chart.js)
        # - bins fixes pour rester stable visuellement
        # - en cas de résidus constants (variance nulle), on garde un range minimal
        bins = 20
        res_min = float(np.min(residuals_test_pts)) if len(residuals_test_pts) else -1.0
        res_max = float(np.max(residuals_test_pts)) if len(residuals_test_pts) else 1.0
        if res_min == res_max:
            res_min -= 1e-6
            res_max += 1e-6
        hist_counts, hist_edges = np.histogram(residuals_test_pts, bins=bins, range=(res_min, res_max))
        residual_hist = {
            "bins": bins,
            "bin_edges_pts": hist_edges.tolist(),
            "counts": hist_counts.astype(int).tolist(),
            "range_pts": [res_min, res_max],
        }
        y_test_mean = float(y_test.mean())
        ss_tot_test = float(((y_test - y_test_mean) ** 2).sum())
        ss_res_test = float(((y_test - y_pred_test) ** 2).sum())
        r2_test = 0.0 if ss_tot_test == 0.0 else (1.0 - ss_res_test / ss_tot_test)

        return jsonify(
            {
                "status": "ok",
                "metrics": {
                    # on expose par défaut la version "test split"
                    "n_samples": n_samples,
                    "n_test": int(len(X_test)),
                    "n_train": int(len(X_train)),
                    "r2": round(r2_test, 6),
                    "r2_full": round(r2_full, 6),
                    "mse": round(mse_test, 6),
                    "rmse": round(rmse_test, 6),
                    "mae": round(mae_test, 6),
                },
                "diagnostics": {
                    "residual_hist_test_2022": residual_hist,
                },
            }
        ), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/cities_predictions", methods=["GET"])
def cities_predictions():
    """
    Retourne pour quelques grandes villes :
    - score_rn 2012 / 2017 / 2022
    - delta (2017 - 2012)
    - prédiction 2027 via le modèle linéaire (ŷ = intercept + b1*2017 + b2*delta)

    But front : alimenter la carte + un graphique d'évolution.
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    # Noms utilisés côté front (carte Leaflet)
    # (si besoin, on peut passer ces noms en paramètre querystring plus tard)
    target_names = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Strasbourg", "Lille"]
    years = (2012, 2017, 2022)

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # 1) Récupérer le codgeo pour chaque ville
        cities = []
        for name in target_names:
            cursor.execute(
                "SELECT codgeo, nom_commune FROM dim_commune WHERE LOWER(nom_commune)=LOWER(%s) LIMIT 1",
                (name,),
            )
            row = cursor.fetchone()
            if row is None:
                # fallback : recherche partielle
                cursor.execute(
                    """
                    SELECT codgeo, nom_commune
                    FROM dim_commune
                    WHERE nom_commune LIKE %s
                    ORDER BY CHAR_LENGTH(nom_commune) ASC
                    LIMIT 1
                    """,
                    (f"%{name}%",),
                )
                row = cursor.fetchone()

            if row:
                cities.append({"name": name, "codgeo": row[0], "nom_commune": row[1]})

        if not cities:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "Aucune ville trouvée dans dim_commune"}), 404

        codgeos = [c["codgeo"] for c in cities]

        # 2) Charger score_rn sur les années utiles
        placeholders = ",".join(["%s"] * len(codgeos))
        cursor.execute(
            f"""
            SELECT codgeo, annee, score_rn
            FROM dataset_ml
            WHERE codgeo IN ({placeholders})
              AND annee IN (%s,%s,%s)
            """,
            tuple(codgeos) + years,
        )
        rows = cursor.fetchall()

        # map (codgeo -> year -> score)
        score_by = {}
        for codgeo, annee, score in rows:
            score_by.setdefault(codgeo, {})[int(annee)] = float(score)

        # 3) Calcul delta + prediction 2027
        result_cities = []
        for c in cities:
            co = c["codgeo"]
            if co not in score_by:
                continue
            scores = score_by[co]
            if not all(y in scores for y in years):
                continue

            score_2012 = scores[2012]
            score_2017 = scores[2017]
            score_2022 = scores[2022]
            delta = score_2017 - score_2012

            # sklearn LinearRegression => features: ["2017","delta"]
            X = pd.DataFrame([[score_2017, delta]], columns=["2017", "delta"])
            pred_2027 = float(model.predict(X)[0])

            result_cities.append(
                {
                    "name": c["name"],
                    "codgeo": c["codgeo"],
                    "score_2012": score_2012,
                    "score_2017": score_2017,
                    "score_2022": score_2022,
                    "delta": delta,
                    "prediction_2027": pred_2027,
                }
            )

        cursor.close()
        connection.close()

        return jsonify({"status": "ok", "cities": result_cities}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/prediction_2027_nationale", methods=["GET"])
def prediction_2027_nationale():
    """
    Reproduit la logique Colab "Moyenne nationale":
    - modèle simplifié entraîné sur X=[2017, delta(2017-2012)] -> y=2022
    - projection 2027 avec:
        feature '2017' = score_2022
        feature 'delta' = score_2022 - score_2017
    Retourne le taux national moyen prédit pour 2027.
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT codgeo, annee, score_rn
            FROM dataset_ml
            WHERE annee IN (2017, 2022)
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        if not rows:
            return jsonify({"status": "error", "message": "dataset_ml vide pour 2017/2022"}), 500

        df = pd.DataFrame(rows, columns=["codgeo", "annee", "score_rn"])
        wide = df.pivot_table(index="codgeo", columns="annee", values="score_rn", aggfunc="first")
        if 2017 not in wide.columns or 2022 not in wide.columns:
            return jsonify({"status": "error", "message": "Années 2017/2022 manquantes"}), 500

        wide = wide.dropna(subset=[2017, 2022]).copy()
        if wide.empty:
            return jsonify({"status": "error", "message": "Aucune commune valide pour projection 2027"}), 500

        # Logique Colab: X_2027_features = {'2017': score_2022, 'delta': score_2022 - score_2017}
        X_2027 = pd.DataFrame(
            {
                "2017": wide[2022].astype(float),
                "delta": (wide[2022] - wide[2017]).astype(float),
            }
        )
        X_2027.columns = X_2027.columns.astype(str)

        pred_2027 = model.predict(X_2027)
        national_mean = float(np.mean(pred_2027))
        n_communes = int(len(X_2027))

        return jsonify(
            {
                "status": "ok",
                "prediction_2027_nationale": round(national_mean, 6),
                "prediction_2027_nationale_pct": round(national_mean * 100.0, 2),
                "n_communes": n_communes,
                "message": "La prédiction concerne le score du RN au premier tour de l'élection présidentielle 2027",
            }
        ), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/kpi_score_mean", methods=["GET"])
def kpi_score_mean():
    """
    KPI 1/7 : Score RN moyen par année (KPI1 global & KPI7 ML).
    Retour: {years: [...], scores: [...]}
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT annee, AVG(score_rn) AS score_moyen
            FROM dataset_ml
            WHERE annee IN (2002, 2007, 2012, 2017, 2022)
            GROUP BY annee
            ORDER BY annee
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        years = [int(r[0]) for r in rows]
        scores = [float(r[1]) for r in rows]
        return jsonify({"status": "ok", "years": years, "scores": scores}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/kpi_top_evolution", methods=["GET"])
def kpi_top_evolution():
    """
    KPI 2 (progrès) : évolution du vote RN = score_rn(2022) - score_rn(2017)
    Top 10 communes.
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
              d.nom_commune AS nom_commune,
              MAX(CASE WHEN dm.annee = 2022 THEN dm.score_rn END)
              - MAX(CASE WHEN dm.annee = 2017 THEN dm.score_rn END) AS evolution
            FROM dataset_ml dm
            INNER JOIN dim_commune d
              ON d.codgeo = dm.codgeo
            WHERE dm.annee IN (2017, 2022)
            GROUP BY d.nom_commune
            ORDER BY evolution DESC
            LIMIT 10
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        top = [
            {"nom_commune": str(r[0]), "evolution": float(r[1])}
            for r in rows
            if r[1] is not None
        ]
        return jsonify({"status": "ok", "top": top}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/kpi_dashboard_overview", methods=["GET"])
def kpi_dashboard_overview():
    """
    KPIs de synthèse (cartes du haut) basés sur dataset_ml :
    - KPI 1 : score RN moyen (2022) + variation vs 2002
    - KPI 2 : évolution moyenne 2017 -> 2022 (par commune)
    - KPI 3 : part des communes en hausse 2017 -> 2022
    - KPI 4 : plus forte progression communale 2017 -> 2022
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # KPI 1 : score moyen par année
        cursor.execute(
            """
            SELECT annee, AVG(score_rn) AS score_moyen
            FROM dataset_ml
            WHERE annee IN (2002, 2007, 2012, 2017, 2022)
            GROUP BY annee
            ORDER BY annee
            """
        )
        rows_years = cursor.fetchall()
        years_avg = {int(r[0]): float(r[1]) for r in rows_years if r[0] is not None and r[1] is not None}

        # KPI 2/3/4 : évolution communale 2017 -> 2022
        cursor.execute(
            """
            SELECT codgeo, annee, score_rn
            FROM dataset_ml
            WHERE annee IN (2017, 2022)
            """
        )
        rows_evo = cursor.fetchall()

        cursor.close()
        connection.close()

        if not rows_evo:
            return jsonify({"status": "error", "message": "dataset_ml vide pour 2017/2022"}), 500

        df = pd.DataFrame(rows_evo, columns=["codgeo", "annee", "score_rn"])
        wide = df.pivot_table(index="codgeo", columns="annee", values="score_rn", aggfunc="first")
        if 2017 not in wide.columns or 2022 not in wide.columns:
            return jsonify({"status": "error", "message": "Années 2017/2022 manquantes dans dataset_ml"}), 500
        wide = wide.dropna(subset=[2017, 2022]).copy()
        if wide.empty:
            return jsonify({"status": "error", "message": "Aucune commune exploitable pour 2017/2022"}), 500

        wide["evolution"] = wide[2022] - wide[2017]
        n_total = int(len(wide))
        n_up = int((wide["evolution"] > 0).sum())
        pct_up = float((n_up / n_total) * 100.0) if n_total > 0 else 0.0
        avg_evolution = float(wide["evolution"].mean())

        best_codgeo = str(wide["evolution"].idxmax())
        best_evolution = float(wide["evolution"].max())

        # Récupère le nom de la commune top progression
        best_commune = best_codgeo
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("SELECT nom_commune FROM dim_commune WHERE codgeo = %s LIMIT 1", (best_codgeo,))
            row = cursor.fetchone()
            if row and row[0]:
                best_commune = str(row[0])
            cursor.close()
            connection.close()
        except mysql.connector.Error:
            # Non bloquant : on garde le codgeo si le nom n'est pas trouvable
            pass

        score_2022 = float(years_avg.get(2022, np.nan))
        score_2002 = float(years_avg.get(2002, np.nan))
        delta_2002_2022 = float(score_2022 - score_2002) if np.isfinite(score_2022) and np.isfinite(score_2002) else np.nan

        return jsonify(
            {
                "status": "ok",
                "kpis": {
                    "score_rn_moyen": {
                        "annee_reference": 2022,
                        "valeur": None if not np.isfinite(score_2022) else round(score_2022, 6),
                        "delta_vs_2002": None if not np.isfinite(delta_2002_2022) else round(delta_2002_2022, 6),
                    },
                    "evolution_moyenne_2017_2022": round(avg_evolution, 6),
                    "communes_en_hausse_2017_2022": {
                        "count": n_up,
                        "total": n_total,
                        "pct": round(pct_up, 4),
                    },
                    "plus_forte_progression_2017_2022": {
                        "nom_commune": best_commune,
                        "evolution": round(best_evolution, 6),
                    },
                },
            }
        ), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/kpi_top_communes_2022", methods=["GET"])
def kpi_top_communes_2022():
    """
    KPI 3 : Top communes RN (annee=2022)
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
              d.nom_commune AS nom_commune,
              dm.score_rn AS score_rn
            FROM dataset_ml dm
            INNER JOIN dim_commune d
              ON d.codgeo = dm.codgeo
            WHERE dm.annee = 2022
            ORDER BY dm.score_rn DESC
            LIMIT 10
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        top = [
            {"nom_commune": str(r[0]), "score_rn": float(r[1])}
            for r in rows
        ]
        return jsonify({"status": "ok", "top": top}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


@app.route("/api/kpi_correlations_2022", methods=["GET"])
def kpi_correlations_2022():
    """
    KPI 4 : Corrélations socio-éco (2022) entre score_rn et revenu_median/population/taux_chomage.
    Retour: {corr: {revenu_median:..., population:..., taux_chomage:...}}
    """
    db_config = get_db_config()
    required_keys = {"host", "user", "password", "database"}
    missing = [k for k, v in db_config.items() if k in required_keys and not v]
    if missing:
        return jsonify({"status": "error", "message": f"Variables manquantes: {', '.join(missing)}"}), 500

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT score_rn, revenu_median, population, taux_chomage
            FROM dataset_ml
            WHERE annee = 2022
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        df = pd.DataFrame(rows, columns=["score_rn", "revenu_median", "population", "taux_chomage"])
        # Retire les NaN si des valeurs de base sont manquantes
        df = df.dropna()
        corr = {
            "revenu_median": float(df["score_rn"].corr(df["revenu_median"])),
            "population": float(df["score_rn"].corr(df["population"])),
            "taux_chomage": float(df["score_rn"].corr(df["taux_chomage"])),
        }
        return jsonify({"status": "ok", "corr": corr}), 200
    except mysql.connector.Error as exc:
        return jsonify({"status": "error", "message": f"Erreur DB: {exc.msg}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
