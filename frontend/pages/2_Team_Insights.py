import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import get_teams
from api import get_squads
from api import get_team_league
from api import get_top_players


st.title("Team Insights")

st.write("Hier kannst du Informationen zu verschiedenen Teams abrufen und analysieren. Entdecke Kader, Statistiken und Leistungsdaten, um dir einen schnellen Überblick zu verschaffen und Teams besser vergleichen zu können.")

# --- Daten laden ---
teams_df = get_teams()

team_options = {
    row["club_name"]: row["club_id"]
    for _, row in teams_df.iterrows()
}

team_name = st.selectbox("Team auswählen", list(team_options.keys()))
team_id = team_options[team_name]

season = st.selectbox(
    "Select Season",
    ["25/26", "24/25", "23/24", "22/23", "21/22", "20/21"]
) 

# --- Tabs ---
tab1, tab2 = st.tabs([
    "Kaderübersicht",
    "Topspieler"
])

league = get_team_league(team_id, season)

with tab1:
    st.subheader("Kaderübersicht")

    if league.empty:
        st.warning("Dieses Team hat in dieser Saison nicht in einer erfassten Liga gespielt.")
    else:
        league_name = league["league"].values[0]
        st.markdown(f"**Liga:** {league_name}")
        
        df = get_squads(team_id, season)
        st.dataframe(df)


with tab2:
    st.subheader("i-AM Topspieler")

    if league.empty:
        st.warning("Keine Daten für diese Saison verfügbar.")
    else:
        df = get_top_players(team_id, season)
        st.dataframe(df)