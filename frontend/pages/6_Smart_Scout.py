import os
import pandas as pd
import streamlit as st

from api import get_iam_scout
from components.header import render_header


POSITION_OPTIONS = [
	"Torwart",
	"Linker Verteidiger",
	"Abwehr",
	"Rechter Verteidiger",
	"Innenverteidiger",
	"Defensives Mittelfeld",
	"Linkes Mittelfeld",
	"Mittelfeld",
	"Offensives Mittelfeld",
	"Zentrales Mittelfeld",
	"Rechtes Mittelfeld",
	"Hängende Spitze",
	"Linksaußen",
	"Mittelstürmer",
	"Rechtsaußen",
	"Sturm",
]


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

tab_myclub, tab_scout_board, tab_player_database = st.tabs([
	"myClub",
	"Scout Board",
	"Spielerdatenbank"
])

with tab_myclub:
	st.subheader("Filter Einstellungen")
	
	# Liga Selection mit Radio Button
	st.write("**Liga**")
	selected_league = st.radio(
		"Wähle deine Liga",
		["1. Liga", "Promotion League"],
		horizontal=True,
		label_visibility="collapsed"
	)
	
	# Ortschaft Selection
	st.write("**Wo ich bin**")
	try:
		postcode_options, postcode_labels = load_postcodes()
		town_options = [postcode_labels[zip_code].split(" - ")[1] for zip_code in postcode_options]
		town_options = sorted(list(set(town_options)))
		
		selected_town = st.selectbox(
			"Ortschaft auswählen",
			town_options,
			label_visibility="collapsed"
		)
	except Exception:
		st.warning("Ortschaften konnten nicht geladen werden.")
		selected_town = None
	
	st.session_state["smart_scout_filters"] = {
		"league": selected_league,
		"town": selected_town,
	}
	st.session_state["smart_scout_filters_draft"] = {
		"league": selected_league,
		"town": selected_town,
	}

with tab_scout_board:
	st.subheader("Spieler Profile")
	with st.expander("Alter", expanded=False):
		# Alter Selection
		st.write("**Alter**")
		
		# Preset Dropdown
		age_preset_map = {
			"Benutzerdefiniert": (18, 28),
			"U21 (16-21)": (16, 21),
			"U25 (22-25)": (22, 25),
			"Prime (26-29)": (26, 29),
			"Erfahren (30+)": (30, 40),
		}
		
		# Initialize session state
		if "age_preset" not in st.session_state:
			st.session_state.age_preset = "Benutzerdefiniert"
		if "age_slider" not in st.session_state:
			st.session_state.age_slider = (18, 28)
		
		# Dropdown selection
		selected_preset = st.selectbox(
			"Altersgruppe",
			list(age_preset_map.keys()),
			index=list(age_preset_map.keys()).index(st.session_state.age_preset),
			label_visibility="collapsed"
		)
		if selected_preset is None:
			selected_preset = "Benutzerdefiniert"
		
		# Update slider when dropdown changes
		slider_value = age_preset_map[selected_preset]
		
		min_age, max_age = st.slider(
			"Altersbereich",
			min_value=14,
			max_value=40,
			value=slider_value,
			step=1,
			label_visibility="collapsed"
		)
		
		current_range = (min_age, max_age)
		
		# Check if slider matches a preset
		matched_preset = "Benutzerdefiniert"
		for label, range_val in age_preset_map.items():
			if label != "Benutzerdefiniert" and range_val == current_range:
				matched_preset = label
				break
		
		# Update session state
		st.session_state.age_preset = matched_preset
		st.session_state.age_slider = current_range
		
		st.session_state["scout_board_filters"] = {
			"age_range": current_range,
		}
		st.session_state["scout_board_filters_draft"] = {
			"age_range": current_range,
		}

	with st.expander("Liga", expanded=False):
		st.write("**Liga**")
		league_1 = st.checkbox("1. Liga Gruppe 1", value=True)
		league_2 = st.checkbox("1. Liga Gruppe 2", value=True)
		league_3 = st.checkbox("1. Liga Gruppe 3", value=True)
		promotion_league = st.checkbox("Promotion League", value=True)

		selected_leagues = []
		if league_1:
			selected_leagues.append("1. Liga Gruppe 1")
		if league_2:
			selected_leagues.append("1. Liga Gruppe 2")
		if league_3:
			selected_leagues.append("1. Liga Gruppe 3")
		if promotion_league:
			selected_leagues.append("Promotion League")

		st.session_state["scout_board_filters"]["leagues"] = selected_leagues
		st.session_state["scout_board_filters_draft"] = {
			**st.session_state.get("scout_board_filters_draft", {}),
			"leagues": selected_leagues,
		}

	with st.expander("Position", expanded=False):
		st.write("**Position**")
		selected_positions = st.multiselect(
			"Positionen auswählen",
			options=POSITION_OPTIONS,
			default=st.session_state.get("scout_board_filters_draft", {}).get("positions", []),
		)
		st.session_state["scout_board_filters"]["positions"] = selected_positions
		st.session_state["scout_board_filters_draft"] = {
			**st.session_state.get("scout_board_filters_draft", {}),
			"positions": selected_positions,
		}

	with st.expander("Entfernung", expanded=False):
		st.write("**Entfernung**")
		use_distance_filter = st.checkbox("Entfernung aktivieren", value=False)
		max_distance_km = st.slider(
			"Maximale Entfernung (km)",
			min_value=5,
			max_value=200,
			value=25,
			step=5,
			disabled=not use_distance_filter,
		)

		st.session_state["scout_board_filters"]["distance_km"] = max_distance_km if use_distance_filter else None
		st.session_state["scout_board_filters"]["distance_enabled"] = use_distance_filter
		st.session_state["scout_board_filters_draft"] = {
			**st.session_state.get("scout_board_filters_draft", {}),
			"distance_km": max_distance_km if use_distance_filter else None,
			"distance_enabled": use_distance_filter,
		}

	if st.button("Use Filter", type="primary"):
		st.session_state["smart_scout_filters"] = dict(st.session_state.get("smart_scout_filters_draft", {}))
		applied_age_range = st.session_state.get("scout_board_filters_draft", {}).get("age_range")
		applied_positions = st.session_state.get("scout_board_filters_draft", {}).get("positions", [])
		applied_leagues = st.session_state.get("scout_board_filters_draft", {}).get("leagues", [])
		applied_distance_km = st.session_state.get("scout_board_filters_draft", {}).get("distance_km")
		applied_distance_enabled = st.session_state.get("scout_board_filters_draft", {}).get("distance_enabled", False)
		st.session_state["scout_board_filters"] = {
			"age_range": applied_age_range,
			"positions": applied_positions,
			"leagues": applied_leagues,
			"distance_km": applied_distance_km,
			"distance_enabled": applied_distance_enabled,
		}
		st.rerun()

with tab_player_database:
	st.subheader("Alle Spieler")
	try:
		myclub_filters = st.session_state.get("smart_scout_filters", {})
		scout_board_filters = st.session_state.get("scout_board_filters", {})
		age_range = scout_board_filters.get("age_range") or (None, None)
		request_params = {}
		if myclub_filters.get("league"):
			request_params["league"] = myclub_filters.get("league")
		if myclub_filters.get("town"):
			request_params["town"] = myclub_filters.get("town")
		if scout_board_filters.get("distance_enabled"):
			request_params["distance_enabled"] = True
			request_params["distance_km"] = scout_board_filters.get("distance_km", 25)
		if age_range[0] is not None and age_range[1] is not None:
			request_params["age_min"] = age_range[0]
			request_params["age_max"] = age_range[1]
		if scout_board_filters.get("positions"):
			request_params["positions"] = scout_board_filters.get("positions", [])
		if scout_board_filters.get("leagues"):
			request_params["leagues"] = scout_board_filters.get("leagues", [])
		players_df = get_iam_scout(params=request_params)
		if players_df.empty:
			st.info("Keine Spieler gefunden.")
		else:
			display_columns = [
				("player_name", "Spieler"),
				("position", "Position"),
				("club_name", "Club"),
				("club_location", "Ort"),
				("age", "Alter"),
				("rating", "Rating"),
			]
			available_columns = [column for column, _ in display_columns if column in players_df.columns]
			display_df = players_df[available_columns].copy()
			display_df = display_df.rename(columns={column: label for column, label in display_columns if column in display_df.columns})
			st.dataframe(display_df, use_container_width=True)
	except Exception as e:
		st.error(f"Fehler beim Laden der Spielerdaten: {e}")