FROM postgres:15

# Run all SQL files automatically on first initialization (alphabetical order).
COPY containers/database/sql/ /docker-entrypoint-initdb.d/

# Keep all SQL scripts available in the image for manual execution if needed.
COPY containers/database/sql/ /opt/db/sql/
