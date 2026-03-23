-- Schéma MySQL pour architecture MSPR
-- Couches : staging -> DWH -> dataset_ml
-- Adapté depuis un design Postgres (remplacement de SERIAL par AUTO_INCREMENT)
--
-- IMPORTANT :
-- - Assure-toi que la base sélectionnée est bien celle que tu utilises (ex: defaultdb).
-- - Les tables dataset_ml sont conçues pour être stables côté entraînement.
-- - Les contraintes NOT NULL impliquent que l'ETL devra fournir des valeurs complètes.

-- Staging
CREATE TABLE IF NOT EXISTS staging_elections (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code_departement VARCHAR(5),
    code_commune VARCHAR(5),
    nom_commune VARCHAR(255),
    annee INT,
    tour INT,

    nom_candidat VARCHAR(255),
    prenom_candidat VARCHAR(255),
    voix FLOAT,
    exprimes FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staging_population (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5),
    population INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staging_revenu (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5),
    revenu_median FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staging_chomage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    region VARCHAR(255),
    taux_chomage FLOAT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staging_communes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5),
    code_departement VARCHAR(5),
    code_commune VARCHAR(5),
    nom_commune VARCHAR(255),
    region VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DWH
CREATE TABLE IF NOT EXISTS dim_commune (
    codgeo VARCHAR(5) NOT NULL PRIMARY KEY,
    code_departement VARCHAR(5) NOT NULL,
    code_commune VARCHAR(5) NOT NULL,
    nom_commune VARCHAR(255) NOT NULL,
    region VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_election (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5) NOT NULL,
    annee INT NOT NULL,

    voix FLOAT NOT NULL,
    exprimes FLOAT NOT NULL,
    score_rn FLOAT NOT NULL,

    UNIQUE KEY uniq_fact_election (codgeo, annee),
    CONSTRAINT fk_fact_election_commune
        FOREIGN KEY (codgeo) REFERENCES dim_commune(codgeo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_population (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5) NOT NULL,
    population INT NOT NULL,

    UNIQUE KEY uniq_fact_population (codgeo),
    CONSTRAINT fk_fact_population_commune
        FOREIGN KEY (codgeo) REFERENCES dim_commune(codgeo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_revenu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codgeo VARCHAR(5) NOT NULL,
    revenu_median FLOAT NOT NULL,

    UNIQUE KEY uniq_fact_revenu (codgeo),
    CONSTRAINT fk_fact_revenu_commune
        FOREIGN KEY (codgeo) REFERENCES dim_commune(codgeo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_chomage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region VARCHAR(255) NOT NULL,
    taux_chomage FLOAT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dataset final ML
-- NOTE : PRIMARY KEY (codgeo, annee) = historisation par année et commune.
CREATE TABLE IF NOT EXISTS dataset_ml (
    codgeo VARCHAR(5) NOT NULL,
    code_departement VARCHAR(5) NOT NULL,
    code_commune VARCHAR(5) NOT NULL,
    nom_commune VARCHAR(255) NOT NULL,
    region VARCHAR(255) NOT NULL,

    annee INT NOT NULL,

    voix FLOAT NOT NULL,
    exprimes FLOAT NOT NULL,
    score_rn FLOAT NOT NULL,

    revenu_median FLOAT NOT NULL,
    population INT NOT NULL,
    taux_chomage FLOAT NOT NULL,

    PRIMARY KEY (codgeo, annee),
    CONSTRAINT fk_dataset_ml_commune
        FOREIGN KEY (codgeo) REFERENCES dim_commune(codgeo)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_dataset_ml_codgeo (codgeo),
    INDEX idx_dataset_ml_annee (annee)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

