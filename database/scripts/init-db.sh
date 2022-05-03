#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER misp;
    CREATE DATABASE misp;
    GRANT ALL PRIVILEGES ON DATABASE misp TO misp;
EOSQL

# create test database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER test_misp;
    CREATE DATABASE test_misp;
    GRANT ALL PRIVILEGES ON DATABASE test_misp TO test_misp;
EOSQL