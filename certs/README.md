# `certs/`

Certificats utilisés pour les connexions SSL/TLS.

## Contenu

- `aiven-ca.pem` : certificat CA pour la connexion MySQL Aiven.

## Utilisation

Le chemin est référencé dans `.env` via :
- `DB_SSL_CA_PATH=certs/aiven-ca.pem`

Ne pas versionner de clés privées dans ce dossier.
