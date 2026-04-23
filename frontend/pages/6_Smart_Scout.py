import os
import pandas as pd
import streamlit as st

from api import get_clubs_in_radius
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

	clubs_df = get_clubs_in_radius(selected_zip, radius_km)
	st.subheader("Clubs im Radius")

	if clubs_df.empty:
		st.info("Keine Clubs im gewählten Radius gefunden.")
	else:
		st.dataframe(clubs_df, use_container_width=True)