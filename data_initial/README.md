# `data_initial/`

Données brutes (sources) utilisées par les scripts :
- `modele_prediction/etl_mspr_to_mysql.py`
- `modele_prediction/mspr1_master.py`

Ne pas modifier les fichiers manuellement après dépôt (source of truth).

## Arborescence attendue

```text
data_initial/
  data-presidentielle/
    resultats-presidentielle-2002.xls
    resultats-presidentielle-2007.xls
    resultats-presidentielle-2012.xls
    resultats-presidentielle-2017.csv
    resultats-presidentielle-2022.xlsx
  population-par-commune-INSEE/
    donnees_communes.csv
  revenu-des-francais-a-la-commune-2021/
    revenu_des_francais_a_la_commune_2021.csv
  Taux-de-chomage/
    taux-de-chomage.xlsx
```

## Bonnes pratiques

- Conserver les noms exacts attendus par les scripts.
- Éviter les renommages et conversions de format sans mise à jour du code.
- Versionner uniquement les fichiers nécessaires au projet.

