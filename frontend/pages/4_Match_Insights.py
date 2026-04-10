import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import get_teams
from api import get_match_search
from api import get_match_overview
from components.header import render_header

render_header("Match Insights")
st.title("Match Insights")

st.write("Hier kannst du detaillierte Informationen zu einzelnen Spielen abrufen. Analysiere Statistiken, Spielverläufe und Leistungen, um Teams und Spieler besser einschätzen und vergleichen zu können.")

teams_df = get_teams()
team_options = {
	row["club_name"]: row["club_id"]
	for _, row in teams_df.iterrows()
}

tab_select, tab_overview = st.tabs([
	"Selektion",
	"Spieluebersicht"
])

with tab_select:
	mode = st.radio(
		"Wie möchtest du ein Spiel finden?",
		["Match-ID eingeben", "Teams auswaehlen"],
		horizontal=True
	)

	if mode == "Match-ID eingeben":
		match_id = st.number_input("Match-ID", min_value=1, step=1)

		if match_id:
			df = get_match_search(match_id=int(match_id))
			if df.empty:
				st.warning("Keine Spiele für diese Match-ID gefunden.")
			else:
				st.session_state["selected_match_id"] = int(match_id)
				st.success("Match-ID gespeichert. Spieluebersicht ist bereit.")
	else:
		if teams_df.empty:
			st.warning("Keine Teams gefunden.")
		else:
			team_a_name = st.selectbox("Team A", list(team_options.keys()))
			team_a_id = team_options[team_a_name]

			team_b_choices = [name for name in team_options.keys() if name != team_a_name]
			team_b_name = st.selectbox("Team B", team_b_choices)
			team_b_id = team_options[team_b_name]

			df = get_match_search(team_a_id=team_a_id, team_b_id=team_b_id)
			if df.empty:
				st.warning("Keine Spiele zwischen diesen Teams gefunden.")
			else:
				match_labels = {
					f"{row['game_date']} - {row['home_team']} vs {row['away_team']} (ID: {row['match_id']})": row["match_id"]
					for _, row in df.iterrows()
				}

				selected_label = st.selectbox("Match auswählen", list(match_labels.keys()))
				selected_match_id = match_labels[selected_label]
				st.session_state["selected_match_id"] = selected_match_id
				st.success(f"Match-ID ausgewählt: {selected_match_id}")

with tab_overview:
	selected_match_id = st.session_state.get("selected_match_id")
	if not selected_match_id:
		st.info("Bitte zuerst ein Match in der Selektion auswaehlen.")
	else:
		df = get_match_overview(selected_match_id)
		if df.empty:
			st.warning("Keine Daten fuer diese Match-ID gefunden.")
		else:
			st.dataframe(df)

