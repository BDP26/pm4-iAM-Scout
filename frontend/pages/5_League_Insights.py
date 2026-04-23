import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import get_leagues_seasons
from api import get_league_top_players
from components.header import render_header

render_header("League Insights")
st.title("League Insights")

df = get_leagues_seasons()

if df.empty:
	st.warning("Keine Liga- und Saisondaten gefunden.")
else:
	league_options = sorted(df["league"].dropna().unique().tolist())
	selected_league = st.selectbox("Liga auswählen", league_options)

	season_options = (
		df[df["league"] == selected_league]["season"]
		.dropna()
		.unique()
		.tolist()
	)
	selected_season = st.selectbox("Saison auswählen", season_options)

	st.subheader("Topspieler der Liga")
	top_players_df = get_league_top_players(selected_league, selected_season)

	if top_players_df.empty:
		st.info("Keine Topspieler-Daten für die gewählte Liga/Saison gefunden.")
	else:
		st.dataframe(top_players_df, use_container_width=True)
