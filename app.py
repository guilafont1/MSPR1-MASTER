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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
