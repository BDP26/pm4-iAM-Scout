import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import get_players
from api import get_player
from api import get_player_stats

st.title("Player Insights")

st.write("Hier kannst du detaillierte Informationen zu einzelnen Spielern abrufen. Analysiere Statistiken, Leistungen und Entwicklungen, um Talente besser einschätzen und vergleichen zu können.")

players_df = get_players()

players_options = {
    row["player_name"]: row["player_id"]
    for _, row in players_df.iterrows()
}

player_name = st.selectbox("Spieler auswählen", list(players_options.keys()))
player_id = players_options[player_name]


# --- Tabs ---
tab1, tab2 = st.tabs([
    "Spielerdaten",
    "Leistungsdaten"
])

with tab1:
    st.subheader("Spielerdaten")

    df = get_player(player_id)

    if df.empty:
        st.warning("Keine Daten gefunden")
    else:
        row = df.iloc[0]

        from datetime import datetime

        dob = row["date_of_birth"]
        if dob:
            dob = datetime.strptime(str(dob), "%Y-%m-%d")
            today = datetime.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        else:
            age = "Unbekannt"

        st.write(f"Name: {row['player_name']}")
        st.write(f"Nationalität: {row['nationality']}")
        st.write(f"Geburtsdatum: {row['date_of_birth']} (Alter: {age})")
        st.write(f"Grösse: {row['height']}")
        st.write(f"Position: {row['position']}")


with tab2:
    st.subheader("Leistungsdaten")

    df = get_player_stats(player_id)

    if df.empty:
        st.warning("Keine Daten gefunden")
    else:
        games = len(df)
        avg_rating = df["rating"].mean()

        col1, col2 = st.columns(2)
        col1.metric("Spiele", games)
        col2.metric("Ø Rating", round(avg_rating, 2) if avg_rating else "N/A")

        st.dataframe(df)
