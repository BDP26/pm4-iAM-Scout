import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import get_teams
from api import get_match_search
from components.header import render_header

render_header("Match Insights")
st.title("Match Insights")

st.write("Hier kannst du detaillierte Informationen zu einzelnen Spielen abrufen. Analysiere Statistiken, Spielverläufe und Leistungen, um Teams und Spieler besser einschätzen und vergleichen zu können.")

teams_df = get_teams()
team_options = {
	row["club_name"]: row["club_id"]
	for _, row in teams_df.iterrows()
}

mode = st.radio(
	"Wie moechtest du ein Spiel finden?",
	["Match-ID eingeben", "Teams auswaehlen"],
	horizontal=True
)

season = st.selectbox(
	"Select Season",
	["25/26", "24/25", "23/24", "22/23", "21/22", "20/21", "Alle"],
	index=0
)

season_value = None if season == "Alle" else season

if mode == "Match-ID eingeben":
	match_id = st.number_input("Match-ID", min_value=1, step=1)

	if match_id:
		df = get_match_search(match_id=int(match_id), season=season_value)
		if df.empty:
			st.warning("Keine Spiele fuer diese Match-ID gefunden.")
		else:
			st.dataframe(df)
else:
	if teams_df.empty:
		st.warning("Keine Teams gefunden.")
	else:
		team_a_name = st.selectbox("Team A", list(team_options.keys()))
		team_a_id = team_options[team_a_name]

		team_b_choices = [name for name in team_options.keys() if name != team_a_name]
		team_b_name = st.selectbox("Team B", team_b_choices)
		team_b_id = team_options[team_b_name]

		df = get_match_search(team_a_id=team_a_id, team_b_id=team_b_id, season=season_value)
		if df.empty:
			st.warning("Keine Spiele zwischen diesen Teams gefunden.")
		else:
			st.dataframe(df)

