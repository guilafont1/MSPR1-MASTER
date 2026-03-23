"""
Dashboard MSPR - Version 1
Application Flask pour le tableau de bord de prédiction électorale nationale.
"""
import os
import warnings
import numpy as np
import pandas as pd
import joblib
import mysql.connector
from flask import Flask, render_template, request, jsonify

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
