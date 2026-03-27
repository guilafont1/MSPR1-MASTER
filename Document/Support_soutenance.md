# Support de soutenance — MSPR Bloc 3 (Big Data & BI)

## Slide 1 — Titre
**Electio-Analytics — POC prédiction électorale (RN 2027)**  
Bloc 3 : Big Data & Business Intelligence  
Équipe : (noms) • Date : (date)

## Slide 2 — Problématique & objectifs
- Besoin client : **anticiper les tendances électorales** à 1–3 ans
- Objectifs POC :
  - collecter & industrialiser un pipeline de données
  - produire des visualisations compréhensibles
  - entraîner/évaluer un modèle prédictif
  - proposer une projection 2027 + métriques de qualité

## Slide 3 — Périmètre & choix
- **Zone** : France entière
- **Granularité** : commune (INSEE `CODGEO`)
- **Années élections** : 2002, 2007, 2012, 2017, 2022
- Hypothèses : socio-éco “photo” (revenu/population) et chômage régional

## Slide 4 — Sources de données (publiques)
- Elections (présidentielles) : votes / exprimés (commune)
- INSEE : population communale + région
- Revenus : revenu médian par commune
- Chômage : taux régional

## Slide 5 — Architecture (Staging → DWH → Dataset ML)
Message clé : **traçabilité + reproductibilité**
- `staging_*` : dépôt & pré-traitements
- `dim_commune` : dimension centrale
- `dataset_ml` : table finale historisée `(codgeo, annee)` pour ML + BI
- ETL : `modele_prediction/etl_mspr_to_mysql.py`
- Schéma : `db/schema_mysql.sql`

## Slide 6 — Modélisation (MCD + étoile)
- MCD métier : Commune, Résultat électoral, Indicateurs, Mesures
- Déclinaison BI :
  - dimension `Commune`
  - fait “Résultat” par année
  - mesures socio-éco dans `dataset_ml`

## Slide 7 — ETL (focus qualité)
- Normalisation identifiants (zfill, extraction digits)
- Gestion arrondissements (Paris/Lyon/Marseille → commune INSEE)
- Cast numériques + suppression lignes incomplètes (respect `NOT NULL`)
- Contrôles :
  - `/health/db`
  - `/api/data_health`

## Slide 8 — Exploration & visualisations (BI)
À montrer en démo :
- KPIs nationaux (score moyen 2022, évolution 2017→2022, top progressions)
- Cartes par département (choroplèthe)
- Analyse socio-éco (scatter + corrélations)
Endpoints (si besoin) :
- `/api/kpi_dashboard_overview`
- `/api/socioeco_map?year=2022`
- `/api/socioeco_insights?year=2022&max_points=900`

## Slide 9 — Modèles testés
Deux niveaux :
- **Régression linéaire** (dashboard / KPIs) : features `2017` + `delta(2017-2012)`
- **Ridge multi-années** (projection 2027) : historique → 2022 + CV  
Artefacts :
- `ridge_multiyear_2027.joblib`
- `ridge_multiyear_2027_metadata.joblib`

## Slide 10 — Évaluation & “accuracy”
Pour une régression :
- Pouvoir prédictif : **\(R^2\)** (attendu > 0,5 selon grille)
- Erreurs : RMSE, MAE + validation croisée
Source affichée :
- `/api/prediction_2027_nationale` (métriques exportées)

## Slide 11 — Résultat principal
- Projection nationale RN 2027 (score %) + \(R^2\) / RMSE / MAE
- Lecture : ce que ça signifie / limites (données socio-éco et granularités)

## Slide 12 — Sécurité / RGPD
- Données publiques agrégées (pas de données personnelles)
- Config via `.env`, accès DB possible en SSL (CA)
- Principes : minimisation, traçabilité, séparation des secrets

## Slide 13 — Limites & pistes d’amélioration
- Historiser `revenu/population/chômage` par année (cohérence temporelle)
- Ajouter d’autres indicateurs (sécurité, pauvreté, associations, dépenses publiques)
- Passer à une granularité chômage plus fine si possible
- Mettre en place tests + CI

## Slide 14 — Démo (plan 2–3 minutes)
- Ouvrir UI (`/`)
- Tableau de bord : KPIs + top progressions
- Analyse : carte socio-éco + insights
- Moteur prédictif : projection 2027 + métriques

## Slide 15 — Conclusion
- POC reproductible : données → ETL → DB → dashboard → modèle
- Livrables : dossier de synthèse, dataset nettoyé, code, support

