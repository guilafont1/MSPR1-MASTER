"""
Dashboard MSPR - Version 1
Application Flask épurée pour la gestion des évaluations et grilles MSPR.
"""
import os
from flask import Flask, render_template

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")


@app.route("/")
def index():
    """Page d'accueil du dashboard."""
    return render_template("index.html")


@app.route("/evaluations")
def evaluations():
    """Évaluations individuelles par le Coach MSPR."""
    return render_template("evaluations.html")


@app.route("/grilles")
def grilles():
    """Grilles MSPR (ex. Bloc 3, I1 EISI)."""
    return render_template("grilles.html")


@app.route("/regles")
def regles():
    """Règles de validation MSPR."""
    return render_template("regles.html")


@app.route("/sujets")
def sujets():
    """Sujets MSPR (ex. Bloc 3, I1 EISI)."""
    return render_template("sujets.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
