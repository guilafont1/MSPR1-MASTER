# -*- coding: utf-8 -*-
"""
ETL MSPR -> MySQL (staging -> DWH -> dataset_ml)

Objectif (compatibilité modèle) :
- Reproduit la logique de `mspr1_master.py` pour calculer `score_rn`
  à l'échelle commune pour les années 2002/2007/2012/2017/2022.
- Marque/merge les variables socio-économiques (revenu_median, population, taux_chomage).
- Charge ensuite `dim_commune` et `dataset_ml` avec des colonnes compatibles
  pour reconstruire `df_wide`/`delta` sans casser le pipeline ML.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Tuple

import mysql.connector
import pandas as pd


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_db_config() -> Dict:
    # Les variables DB_* viennent soit de l'environnement docker-compose,
    # soit du fichier `.env` exporté dans le shell.
    return {
        "host": os.environ.get("DB_HOST"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_NAME"),
        "ssl_ca": os.environ.get("DB_SSL_CA_PATH"),
        "connection_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "10")),
    }


def require_files(paths: Dict[str, Path]) -> None:
    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        pretty = ", ".join([f"{k}={paths[k]}" for k in missing])
        raise FileNotFoundError(f"Fichiers manquants pour ETL : {pretty}")


def extract_rn_communes_2022(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    base_cols = [
        "Code du département",
        "Libellé du département",
        "Code de la circonscription",
        "Libellé de la circonscription",
        "Code de la commune",
        "Libellé de la commune",
        "Code du b.vote",
        "Inscrits",
        "Exprimés",
    ]

    start = list(df.columns).index("N°Panneau")

    df_long_parts = []
    for i in range(0, 84, 7):
        cols = df.columns[start + i : start + i + 7]
        temp = df[base_cols + list(cols)].copy()
        temp.columns = base_cols + [
            "N°Panneau",
            "Sexe",
            "Nom",
            "Prénom",
            "Voix",
            "%Voix/Ins",
            "%Voix/Exp",
        ]
        df_long_parts.append(temp)

    df_long = pd.concat(df_long_parts)
    rn_df = df_long[df_long["Nom"].str.contains("LE PEN", case=False, na=False)].copy()

    rn_communes = (
        rn_df.groupby(["Code du département", "Code de la commune", "Libellé de la commune"])
        .agg({"Voix": "sum", "Exprimés": "sum"})
        .reset_index()
    )
    rn_communes["score_rn"] = rn_communes["Voix"] / rn_communes["Exprimés"]
    rn_communes["annee"] = 2022
    return rn_communes


def extract_rn_communes_2017(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=",", low_memory=False)

    base_cols = ["Code du département", "Code de la commune", "Libellé de la commune", "Exprimés"]
    start = list(df.columns).index("N°Panneau")

    df_long_parts = []
    for i in range(0, 77, 7):
        cols = df.columns[start + i : start + i + 7]
        temp = df[base_cols + list(cols)].copy()
        temp.columns = base_cols + [
            "N°Panneau",
            "Sexe",
            "Nom",
            "Prénom",
            "Voix",
            "%Voix/Ins",
            "%Voix/Exp",
        ]
        df_long_parts.append(temp)

    df_long = pd.concat(df_long_parts)
    rn_df = df_long[df_long["Nom"].str.contains("PEN", case=False, na=False)].copy()

    rn_communes = (
        rn_df.groupby(["Code du département", "Code de la commune", "Libellé de la commune"])
        .agg({"Voix": "sum", "Exprimés": "sum"})
        .reset_index()
    )
    rn_communes["score_rn"] = rn_communes["Voix"] / rn_communes["Exprimés"]
    rn_communes["annee"] = 2017
    return rn_communes


def extract_rn_communes_2012(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="xlrd")

    base_cols = ["Code du département", "Code de la commune", "Libellé de la commune", "Exprimés"]

    df_long_parts = []
    for i in range(0, 10):
        suffix = "" if i == 0 else f".{i}"
        cols = [f"Sexe{suffix}", f"Nom{suffix}", f"Prénom{suffix}", f"Voix{suffix}"]
        cols_exist = [c for c in cols if c in df.columns]
        if len(cols_exist) < 4:
            continue

        temp = df[base_cols + cols_exist].copy()
        temp.columns = base_cols + ["Sexe", "Nom", "Prénom", "Voix"]
        df_long_parts.append(temp)

    df_long = pd.concat(df_long_parts)
    rn_df = df_long[df_long["Nom"].str.contains("PEN", case=False, na=False)].copy()
    rn_df["Voix"] = pd.to_numeric(rn_df["Voix"], errors="coerce")
    rn_df["Exprimés"] = pd.to_numeric(rn_df["Exprimés"], errors="coerce")

    rn_communes = (
        rn_df.groupby(["Code du département", "Code de la commune", "Libellé de la commune"])
        .agg({"Voix": "sum", "Exprimés": "sum"})
        .reset_index()
    )
    rn_communes["score_rn"] = rn_communes["Voix"] / rn_communes["Exprimés"]
    rn_communes["annee"] = 2012
    return rn_communes


def extract_rn_communes_2007(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="xlrd")

    base_cols = ["Code du département", "Code de la commune", "Libellé de la commune", "Exprimés"]

    df_long_parts = []
    for i in range(0, 15):
        suffix = "" if i == 0 else f".{i}"
        cols = [f"Sexe{suffix}", f"Nom{suffix}", f"Prénom{suffix}", f"Voix{suffix}"]
        if not all(col in df.columns for col in cols):
            continue

        temp = df[base_cols + cols].copy()
        temp.columns = base_cols + ["Sexe", "Nom", "Prénom", "Voix"]
        df_long_parts.append(temp)

    df_long = pd.concat(df_long_parts)
    rn_df = df_long[df_long["Nom"].str.contains("PEN", case=False, na=False)].copy()
    rn_df["Voix"] = pd.to_numeric(rn_df["Voix"], errors="coerce")
    rn_df["Exprimés"] = pd.to_numeric(rn_df["Exprimés"], errors="coerce")

    rn_communes = (
        rn_df.groupby(["Code du département", "Code de la commune", "Libellé de la commune"])
        .agg({"Voix": "sum", "Exprimés": "sum"})
        .reset_index()
    )
    rn_communes["score_rn"] = rn_communes["Voix"] / rn_communes["Exprimés"]
    rn_communes["annee"] = 2007
    return rn_communes


def extract_rn_communes_2002(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="xlrd")

    base_cols = ["Code du département", "Code de la commune", "Libellé de la commune", "Exprimés"]

    # candidat 1
    temp1 = df[base_cols + ["Nom", "Prénom", "Voix"]].copy()
    temp1.columns = base_cols + ["Nom", "Prénom", "Voix"]

    # candidat 2 (suffix .1 → LE PEN ici)
    temp2 = df[base_cols + ["Nom.1", "Prénom.1", "Voix.1"]].copy()
    temp2.columns = base_cols + ["Nom", "Prénom", "Voix"]

    df_long = pd.concat([temp1, temp2])
    rn_df = df_long[df_long["Nom"].str.contains("PEN", case=False, na=False)].copy()
    rn_df["Voix"] = pd.to_numeric(rn_df["Voix"], errors="coerce")
    rn_df["Exprimés"] = pd.to_numeric(rn_df["Exprimés"], errors="coerce")

    rn_communes = (
        rn_df.groupby(["Code du département", "Code de la commune", "Libellé de la commune"])
        .agg({"Voix": "sum", "Exprimés": "sum"})
        .reset_index()
    )
    rn_communes["score_rn"] = rn_communes["Voix"] / rn_communes["Exprimés"]
    rn_communes["annee"] = 2002
    return rn_communes


def build_dataset_ml_from_files(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    election_dir = data_dir / "data-presidentielle"
    pop_path = data_dir / "population-par-commune-INSEE" / "donnees_communes.csv"
    revenu_path = data_dir / "revenu-des-francais-a-la-commune-2021" / "revenu_des_francais_a_la_commune_2021.csv"
    chomage_path = data_dir / "Taux-de-chomage" / "taux-de-chomage.xlsx"

    paths = {
        "election_2002": election_dir / "resultats-presidentielle-2002.xls",
        "election_2007": election_dir / "resultats-presidentielle-2007.xls",
        "election_2012": election_dir / "resultats-presidentielle-2012.xls",
        "election_2017": election_dir / "resultats-presidentielle-2017.csv",
        "election_2022": election_dir / "resultats-presidentielle-2022.xlsx",
        "population": pop_path,
        "revenu": revenu_path,
        "chomage": chomage_path,
    }
    require_files(paths)

    rn_2002 = extract_rn_communes_2002(paths["election_2002"])
    rn_2007 = extract_rn_communes_2007(paths["election_2007"])
    rn_2012 = extract_rn_communes_2012(paths["election_2012"])
    rn_2017 = extract_rn_communes_2017(paths["election_2017"])
    rn_2022 = extract_rn_communes_2022(paths["election_2022"])

    df_global = pd.concat([rn_2002, rn_2007, rn_2012, rn_2017, rn_2022]).reset_index(drop=True)

    df_global["Voix"] = pd.to_numeric(df_global["Voix"], errors="coerce")
    df_global["Exprimés"] = pd.to_numeric(df_global["Exprimés"], errors="coerce")
    df_global["score_rn"] = pd.to_numeric(df_global["score_rn"], errors="coerce")
    df_global = df_global.dropna(subset=["score_rn", "Voix", "Exprimés"])

    # INSEE - population + région
    df_pop = pd.read_csv(pop_path, sep=";")
    df_pop["CODGEO"] = df_pop["DEP"].astype(str).str.zfill(2) + df_pop["CODCOM"].astype(str).str.zfill(3)

    # normalisation codes comme dans mspr1_master.py
    df_global["Code du département"] = df_global["Code du département"].astype(str).str.zfill(2)
    df_global["Code de la commune"] = (
        df_global["Code de la commune"].astype(str).str.extract(r"(\d+)")[0].str.zfill(3)
    )
    df_global["CODGEO"] = df_global["Code du département"] + df_global["Code de la commune"]

    df = df_global.merge(df_pop[["CODGEO", "PTOT"]], on="CODGEO", how="left")
    df = df.rename(columns={"PTOT": "population"})

    # Revenu
    df_rev = pd.read_csv(revenu_path, sep=";")
    df_rev_clean = df_rev[["Code géographique", "[DISP] Médiane (€)"]].copy()
    df_rev_clean.columns = ["CODGEO", "revenu_median"]
    df_rev_clean["CODGEO"] = df_rev_clean["CODGEO"].astype(str).str.zfill(5)
    df_rev_clean["revenu_median"] = pd.to_numeric(df_rev_clean["revenu_median"], errors="coerce")

    df_merged = df.merge(df_rev_clean, on="CODGEO", how="left")

    # Chômage (région)
    df_chomage = pd.read_excel(chomage_path, skiprows=4, header=None)
    df_chomage_clean = df_chomage.iloc[:, [0, 6]].copy()
    df_chomage_clean.columns = ["Région", "taux_chomage"]
    df_chomage_clean = df_chomage_clean.dropna()
    df_chomage_clean = df_chomage_clean[~df_chomage_clean["Région"].str.contains("France", na=False)]

    df_merged_with_region = df_merged.merge(
        df_pop[["CODGEO", "Région"]].drop_duplicates(subset=["CODGEO"]),
        on="CODGEO",
        how="left",
    )
    df_final = df_merged_with_region.merge(df_chomage_clean, on="Région", how="left")

    # Extraction colonnes alignées sur dataset_ml
    out_cols = [
        "CODGEO",
        "Code du département",
        "Code de la commune",
        "Libellé de la commune",
        "Région",
        "annee",
        "Voix",
        "Exprimés",
        "score_rn",
        "revenu_median",
        "population",
        "taux_chomage",
    ]
    missing_cols = [c for c in out_cols if c not in df_final.columns]
    if missing_cols:
        raise KeyError(f"Colonnes manquantes dans df_final: {missing_cols}")

    df_ml = df_final[out_cols].copy()
    df_ml["Voix"] = pd.to_numeric(df_ml["Voix"], errors="coerce")
    df_ml["Exprimés"] = pd.to_numeric(df_ml["Exprimés"], errors="coerce")
    df_ml["score_rn"] = pd.to_numeric(df_ml["score_rn"], errors="coerce")
    df_ml["revenu_median"] = pd.to_numeric(df_ml["revenu_median"], errors="coerce")
    df_ml["population"] = pd.to_numeric(df_ml["population"], errors="coerce")
    df_ml["taux_chomage"] = pd.to_numeric(df_ml["taux_chomage"], errors="coerce")

    # dataset_ml exige NOT NULL : on drop les lignes incomplètes
    df_ml = df_ml.dropna(
        subset=[
            "CODGEO",
            "Code du département",
            "Code de la commune",
            "Libellé de la commune",
            "Région",
            "annee",
            "Voix",
            "Exprimés",
            "score_rn",
            "revenu_median",
            "population",
            "taux_chomage",
        ]
    )

    df_dim = df_ml[
        ["CODGEO", "Code du département", "Code de la commune", "Libellé de la commune", "Région"]
    ].drop_duplicates(subset=["CODGEO"])

    return df_ml, df_dim


def upsert_dim_commune(conn: mysql.connector.MySQLConnection, df_dim: pd.DataFrame) -> None:
    sql = """
        INSERT INTO dim_commune (codgeo, code_departement, code_commune, nom_commune, region)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            code_departement = VALUES(code_departement),
            code_commune = VALUES(code_commune),
            nom_commune = VALUES(nom_commune),
            region = VALUES(region)
    """
    values = [
        (
            str(r["CODGEO"]),
            str(r["Code du département"]),
            str(r["Code de la commune"]),
            str(r["Libellé de la commune"]),
            str(r["Région"]),
        )
        for _, r in df_dim.iterrows()
    ]
    cur = conn.cursor()
    cur.executemany(sql, values)
    conn.commit()
    cur.close()


def upsert_dataset_ml(conn: mysql.connector.MySQLConnection, df_ml: pd.DataFrame) -> None:
    sql = """
        INSERT INTO dataset_ml (
            codgeo, code_departement, code_commune, nom_commune, region,
            annee,
            voix, exprimes, score_rn,
            revenu_median, population, taux_chomage
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            voix = VALUES(voix),
            exprimes = VALUES(exprimes),
            score_rn = VALUES(score_rn),
            revenu_median = VALUES(revenu_median),
            population = VALUES(population),
            taux_chomage = VALUES(taux_chomage),
            nom_commune = VALUES(nom_commune),
            region = VALUES(region),
            code_departement = VALUES(code_departement),
            code_commune = VALUES(code_commune)
    """
    values = []
    for _, r in df_ml.iterrows():
        values.append(
            (
                str(r["CODGEO"]),
                str(r["Code du département"]),
                str(r["Code de la commune"]),
                str(r["Libellé de la commune"]),
                str(r["Région"]),
                int(r["annee"]),
                float(r["Voix"]),
                float(r["Exprimés"]),
                float(r["score_rn"]),
                float(r["revenu_median"]),
                int(r["population"]),
                float(r["taux_chomage"]),
            )
        )

    cur = conn.cursor()
    # Chunk pour éviter des paquets trop gros
    chunk_size = 2000
    for i in range(0, len(values), chunk_size):
        cur.executemany(sql, values[i : i + chunk_size])
        conn.commit()
    cur.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data_initial", help="Dossier contenant les CSV/Excel bruts")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Construit les DataFrames mais n'insère pas en base",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    data_dir = (repo_root / args.data_dir).resolve()
    if not data_dir.exists():
        raise FileNotFoundError(f"--data-dir introuvable : {data_dir}")

    print("[ETL] Construction des DataFrames (score_rn + merges socio-éco)...")
    df_ml, df_dim = build_dataset_ml_from_files(data_dir)
    print(f"[ETL] df_ml: {len(df_ml)} lignes ; df_dim: {len(df_dim)} communes")

    if args.dry_run:
        print("[ETL] Dry-run : insertion ignorée.")
        return

    cfg = get_db_config()
    missing = [k for k in ["host", "user", "password", "database"] if not cfg.get(k)]
    if missing:
        raise ValueError(f"Variables DB manquantes (ex: DB_HOST/DB_USER/DB_PASSWORD/DB_NAME) : {missing}")

    print("[ETL] Connexion MySQL...")
    conn = mysql.connector.connect(**cfg)
    try:
        print("[ETL] Upsert dim_commune...")
        upsert_dim_commune(conn, df_dim)

        print("[ETL] Upsert dataset_ml...")
        upsert_dataset_ml(conn, df_ml)

        print("[ETL] OK.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

