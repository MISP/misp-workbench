#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER misp;
    CREATE DATABASE misp;
    GRANT ALL PRIVILEGES ON DATABASE misp TO misp;
EOSQL