import streamlit as st

def render_header(page_title=None):
    col1, col2 = st.columns([1, 8])

def render_header(page_title=None):
    col1, col2, col3 = st.columns([1, 6, 3])

def render_header(page_title=None):
    col1, col2, col3 = st.columns([1, 6, 3])

    with col1:
        st.image("assets/Square.png", width=60)

    with col2:
        st.markdown(
            "<h4 style='margin-bottom:0;'>iAM-Scout</h4>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='margin-top:0; margin-bottom:0; font-size:12px; color:gray;'>Amateur Football Scouting</p>",
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            "<p style='margin-top:22px; margin-bottom:0; text-align:right; font-size:12px; color:gray;'>Fabian Meier · Cedric Niklaus</p>",
            unsafe_allow_html=True
        )

    st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)




