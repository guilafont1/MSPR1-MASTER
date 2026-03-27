# Dossier de synthèse — MSPR Bloc 3 (Big Data & BI)

## 1) Contexte & objectif
**Client (fictif)** : Electio-Analytics (conseil stratégique campagnes électorales).  
**Objectif du POC** : valider la faisabilité d’une approche de **prévision de tendances électorales** à partir de données publiques (élections + indicateurs socio-économiques) et produire une restitution exploitable.

## 2) Périmètre géographique
Le POC est réalisé sur **la France entière** avec une granularité **commune** (INSEE `CODGEO` = département + commune).  
Justification :
- disponibilité des jeux de données (résultats présidentiels + INSEE),
- comparaison multi-années homogène,
- traçabilité via identifiant unique `CODGEO`.

## 3) Données & critères retenus
### Sources (données publiques)
- **Élections présidentielles** (2002, 2007, 2012, 2017, 2022) : `data_initial/data-presidentielle/`
- **Population communale** (INSEE) : `data_initial/population-par-commune-INSEE/donnees_communes.csv`
- **Revenu médian** (commune) : `data_initial/revenu-des-francais-a-la-commune-2021/revenu_des_francais_a_la_commune_2021.csv`
- **Taux de chômage** (région) : `data_initial/Taux-de-chomage/taux-de-chomage.xlsx`

### Variables / indicateurs exploités
- **Cible (vote)** : `score_rn = voix / exprimes` par commune et par année.
- **Socio-économiques** : `revenu_median`, `population`, `taux_chomage`.

### Hypothèses (nécessaires pour le POC)
- `revenu_median` et `population` sont utilisés comme **photo récente** (non historisée dans le DWH actuel).
- `taux_chomage` est à granularité **région** et appliqué aux communes via leur région (risque de pouvoir explicatif limité).

## 4) Démarche & méthodes
### 4.1 Pipeline de traitement (ETL)
- **Ingestion** des sources brutes (`data_initial/`).
- **Normalisation** des codes (zfill, extraction numérique) + gestion des cas d’arrondissements (Paris/Lyon/Marseille) dans l’ETL.
- **Calcul** du `score_rn` communal pour chaque année.
- **Jointures** socio-éco (commune/année, ou commune/région) puis filtration `NOT NULL`.

Scripts :
- ETL vers MySQL : `modele_prediction/etl_mspr_to_mysql.py`
- Création schéma : `db/schema_mysql.sql`

### 4.2 Stockage & architecture BI
Architecture en couches :
- **Staging** : tables `staging_*` (zone d’atterrissage / préparation)
- **DWH** : dimension `dim_commune` + faits `fact_*`
- **Dataset ML** : table `dataset_ml` (dénormalisée, historisée par `(codgeo, annee)`), stable côté entraînement et restitution

## 5) Modèle Conceptuel de Données (MCD) + déclinaison décisionnelle
### 5.1 MCD (niveau métier)
Entités principales :
- **Commune** (identifiant `CODGEO`, nom, département, région)
- **Résultat électoral** (année, voix, exprimés, score)
- **Indicateur socio-économique** (type indicateur) + **Mesure** (valeur, période, zone)

Associations (cardinalités attendues) :
- Commune **1..1** — **0..N** Résultats électoraux
- Commune **1..1** — **0..N** Mesures d’indicateurs

### 5.2 Modèle décisionnel (étoile)
Pour la BI, le modèle est décliné en étoile autour de la commune :
- **Dimension** : `dim_commune`
- **Fait principal** : résultats `score_rn` par année (table `dataset_ml` ou `fact_election`)
- **Mesures associées** : revenu / population / chômage (dans `dataset_ml`)

Référence schéma physique : `db/schema_mysql.sql`.

## 6) Modèles testés (machine learning)
### 6.1 Approche
Deux approches coexistent dans le POC :
- **Modèle simple (dashboard)** : régression linéaire (features `score_2017` + `delta = score_2017 - score_2012`) utilisée pour les KPI et certaines vues.
- **Modèle “projection 2027” (référence)** : **Ridge** multi-années (2002/2007/2012/2017 → 2022), avec export d’artefacts.

Scripts & artefacts :
- Entraînement / export : `modele_prediction/mspr1_master.py`
- Export modèle + métriques :  
  - `modele_prediction/ridge_multiyear_2027.joblib`  
  - `modele_prediction/ridge_multiyear_2027_metadata.joblib`

### 6.2 Validation / métrique (accuracy)
Pour un problème de régression, la “précision” est formalisée via **\(R^2\)** (pouvoir prédictif).  
Le front expose les métriques du modèle Ridge exporté :
- `R² test`, `RMSE test`, `MAE test`, `R² CV mean/std`, `n_samples`

Endpoint : `/api/prediction_2027_nationale` (source **uniquement** = metadata exportées).

## 7) Résultats & interprétation
### 7.1 Résultats attendus
- **Projection nationale 2027** (score RN 1er tour) : affichée dans la vue “Moteur prédictif”.
- **KPIs nationaux** (moyennes, évolutions, top communes) : vue “Tableau de bord”.
- **Analyse socio-éco** :
  - corrélations Pearson (`score_rn` vs revenu/population/chômage),
  - cartes par département (agrégations) et scatters (communes échantillonnées).

### 7.2 Interprétation (points clés)
- Les indicateurs socio-éco (notamment chômage régional) peuvent expliquer **une partie** des écarts, mais restent limités par la granularité.
- Le modèle Ridge multi-années permet une projection cohérente en exploitant l’historique (tendance/volatilité).

## 8) Visualisations (restitution)
UI web Flask (front principal : `templates/index.html`) :
- **Carte France** + KPIs (overview)
- **Courbe “score RN moyen”** par année (2002→2022)
- **Top progressions 2017→2022**
- **Cartes choroplèthes par département** (score/chômage/revenu) + tooltips

API (exemples) :
- `/api/kpi_dashboard_overview`
- `/api/kpi_score_mean`
- `/api/kpi_top_evolution`
- `/api/socioeco_map?year=2022`
- `/api/socioeco_insights?year=2022&max_points=900`

## 9) Qualité des données (nettoyage / traçabilité)
Mesures mises en place :
- normalisation des identifiants (zfill, mapping arrondissements → commune INSEE),
- conversions numériques + suppression des lignes incomplètes (`dropna`) pour respecter `NOT NULL`,
- table `dataset_ml` **référentielle et historisée** (`PRIMARY KEY (codgeo, annee)`).

Contrôles disponibles :
- santé DB : `/health/db`
- indicateurs “Data Health” (complétude, couverture temporelle, traçabilité, exactitude proxy) : `/api/data_health`

## 10) Sécurité & conformité (RGPD)
- Données utilisées : **données publiques agrégées** (communes/départements), sans données personnelles.
- Recommandations appliquées :
  - séparation config via variables d’environnement (`.env`),
  - accès DB chiffré possible (SSL CA : `certs/aiven-ca.pem`),
  - aucune clé/secrets à committer (voir `.gitignore`).

## 11) Réponses aux questions d’analyse (attendus du sujet)
- **Donnée la plus corrélée** aux résultats : à justifier via `/api/kpi_correlations_2022` et la vue “Analyse Socio-éco”.
- **Principe apprentissage supervisé** : apprentissage d’une fonction \(f(X)\rightarrow y\) à partir d’exemples étiquetés (historique 2002→2022) puis évaluation sur un jeu de test.
- **Degré de précision** : ici via **\(R^2\)** (pouvoir prédictif), et erreurs `RMSE/MAE` sur test + validation croisée (CV).

## 12) Livrables remis (mapping sujet)
- **Dossier de synthèse** : ce document.
- **Jeu de données nettoyé / normalisé** : `dataset_ml` (MySQL) et sorties intermédiaires `modele_prediction/outputs/*.csv`.
- **Code** : repo complet (ETL + app + modèle).
- **Support de soutenance** : `Document/Support_soutenance.md` (à copier dans PPT/Canva).

