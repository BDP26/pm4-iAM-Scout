#!/bin/sh
set -eu

echo "Waiting for Postgres..."

until pg_isready -h postgres -p 5432 -U postgres -d iamscout; do
  sleep 2
done

run_sql_if_file_exists() {
  csv_path="$1"
  sql_path="$2"
  label="$3"

  if [ -f "$csv_path" ]; then
    echo "Upserting $label from $csv_path ..."
    psql -h postgres -U postgres -d iamscout -v ON_ERROR_STOP=1 -f "$sql_path"
  else
    echo "Skipping $label. File not found: $csv_path"
  fi
}

run_sql_if_file_exists /data/transform/clubs.csv /opt/update_data/sql/20_upsert_clubs.sql "clubs"
run_sql_if_file_exists /data/transform/clubs_per_season.csv /opt/update_data/sql/21_upsert_clubs_per_season.sql "clubs_per_season"
run_sql_if_file_exists /data/transform/players.csv /opt/update_data/sql/22_upsert_players.sql "players"
run_sql_if_file_exists /data/transform/squads.csv /opt/update_data/sql/23_upsert_squads.sql "squads"
run_sql_if_file_exists /data/transform/matches.csv /opt/update_data/sql/24_upsert_matches.sql "matches"
run_sql_if_file_exists /data/transform/player_stats.csv /opt/update_data/sql/25_upsert_player_stats.sql "player_stats"

echo "Incremental update completed successfully."