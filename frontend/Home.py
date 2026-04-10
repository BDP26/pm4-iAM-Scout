import streamlit as st
from api import API_URL
from components.header import render_header

st.set_page_config(
    page_title="iAM-Scout",
    page_icon="assets/Sqare_transparent.png",
    layout="wide"
)

render_header()
st.title("Entdecke Talente im Amateurfussball")

st.write("""
iAM-Scout ermöglicht datenbasierte Spieleranalyse im Amateurbereich.  
Finde Spieler, analysiere Leistungen und entdecke verborgene Talente.
""")

st.header("Was kannst du hier machen?")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("🏟️ Team Insights")
    st.write("Entdecke Teams, Kader und ihre Leistungen auf einen Blick.")
    if st.button("Teams analysieren", use_container_width=True):
        st.switch_page("pages/2_Team_Insights.py")

with col2:
    st.subheader("👤 Player Insights")
    st.write("Erhalte detaillierte Statistiken und Bewertungen von Spielern.")
    if st.button("Spieler entdecken", use_container_width=True):
        st.switch_page("pages/3_Player_Insights.py")

with col3:
    st.subheader("⚽ Match Insights")
    st.write("Analysiere Spiele, Ergebnisse und Match-Statistiken im Detail.")
    if st.button("Matches analysieren", use_container_width=True):
        st.switch_page("pages/4_Match_Insights.py")

with col4:
    st.subheader("🧠 Smart Scout")
    st.write("Finde automatisch passende Spieler basierend auf deinen Kriterien.")
    if st.button("Smart Scout starten", use_container_width=True):
        st.switch_page("pages/4_Smart_Scout.py")



st.header("Warum iAM-Scout?")
st.write("""
Im Gegensatz zu klassischen Plattformen liegt der Fokus auf dem Amateurfussball –  
dort, wo Talent oft unentdeckt bleibt.
""")


