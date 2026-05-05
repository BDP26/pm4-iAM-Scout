import os
import pandas as pd
import streamlit as st

from api import get_clubs_in_radius, get_iam_scout
from components.header import render_header


@st.cache_data
def load_postcodes():
	csv_path = os.path.abspath(
		os.path.join(os.path.dirname(__file__), "..", "assets", "post-codes.csv")
	)
	df = pd.read_csv(csv_path, dtype={"zip": str})
	df = df[["zip", "town"]].dropna()
	df["zip"] = df["zip"].astype(str).str.strip()
	df["town"] = df["town"].astype(str).str.strip()
	df = df.sort_values(["zip", "town"]).drop_duplicates(subset=["zip"], keep="first")

	postcodes = df["zip"].tolist()
	labels = {row["zip"]: f"{row['zip']} - {row['town']}" for _, row in df.iterrows()}
	return postcodes, labels


render_header("Smart Scout")
st.title("Smart Scout")

tab_filter, tab_player_database = st.tabs([
	"Filter",
	"Spielerdatenbank"
])

with tab_filter:
	try:
		postcode_options, postcode_labels = load_postcodes()
	except Exception:
		postcode_options = []
		postcode_labels = {}

	if not postcode_options:
		st.warning("Keine Postleitzahlen gefunden.")
	else:
		selected_zip = st.selectbox(
			"Postleitzahl auswählen",
			postcode_options,
			format_func=lambda value: postcode_labels.get(value, value),
		)

		radius_km = st.slider(
			"Radius (km)",
			min_value=5,
			max_value=100,
			value=25,
			step=5,
		)

		st.subheader("Weitere Filter")

		age_categories = [
			"Egal",
			"U17 (14-17)",
			"U21 (18-21)",
			"U25 (22-25)",
			"Prime (26-29)",
			"Erfahren (30+)",
		]
		selected_age_category = st.selectbox("Alterskategorie", age_categories)

		position_options = [
			"Torwart",
			"Innenverteidiger",
			"Aussenverteidiger",
			"Defensives Mittelfeld",
			"Zentrales Mittelfeld",
			"Offensives Mittelfeld",
			"Fluegel",
			"Stuermer",
		]
		selected_positions = st.multiselect("Positionen (leer = egal)", position_options)

		league_options = [
			"Egal",
			"Promotion League",
			"1. Liga",
		]
		selected_league = st.selectbox("Liga", league_options)

		use_min_games_filter = st.checkbox("Mindestanzahl Spiele anwenden", value=False)
		min_games_last_season = st.slider(
			"Spiele in der letzten Saison (mindestens)",
			min_value=0,
			max_value=40,
			value=10,
			step=1,
			disabled=not use_min_games_filter,
		)

		age_filter_value = None if selected_age_category == "Egal" else selected_age_category
		league_filter_value = None if selected_league == "Egal" else selected_league
		positions_filter_value = selected_positions if selected_positions else None
		min_games_filter_value = min_games_last_season if use_min_games_filter else None

		st.session_state["smart_scout_filters"] = {
			"zip_code": selected_zip,
			"radius_km": radius_km,
			"age_category": age_filter_value,
			"positions": positions_filter_value,
			"league": league_filter_value,
			"min_games_last_season": min_games_filter_value,
		}

		clubs_df = get_clubs_in_radius(selected_zip, radius_km)
		st.subheader("Clubs im Radius")

		if clubs_df.empty:
			st.info("Keine Clubs im gewählten Radius gefunden.")
		else:
			st.dataframe(clubs_df, use_container_width=True)

with tab_player_database:
	st.subheader("Alle Spieler")
	try:
		players_df = get_iam_scout()
		if players_df.empty:
			st.info("Keine Spieler gefunden.")
		else:
			st.dataframe(players_df, use_container_width=True)
	except Exception as e:
		st.error(f"Fehler beim Laden der Spielerdaten: {e}")