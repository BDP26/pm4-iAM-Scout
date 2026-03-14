FROM postgres:15

# Only initialize schema automatically; keep DB independent from transform data loading.
COPY containers/database/sql/01_schema.sql /docker-entrypoint-initdb.d/01_schema.sql

# Keep all SQL scripts available in the image for manual execution if needed.
COPY containers/database/sql/ /opt/db/sql/
