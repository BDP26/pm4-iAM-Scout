import streamlit as st

LOGO_PATH = "assets/Square.png"
APP_NAME = "iAM-Scout"
DEFAULT_PAGE_TITLE = "Amateur Football Scouting"
AUTHORS_TEXT = "Fabian Meier · Cedric Niklaus"
HEADER_COLUMN_LAYOUT = [1, 6, 3]
LOGO_WIDTH = 60


def render_html(content: str) -> None:
    """Render trusted HTML content in Streamlit."""
    st.markdown(content, unsafe_allow_html=True)


def render_logo() -> None:
    """Render the application logo."""
    st.image(LOGO_PATH, width=LOGO_WIDTH)


def render_branding(page_title: str | None = None) -> None:
    """Render the application name and page subtitle."""
    subtitle = page_title or DEFAULT_PAGE_TITLE

    render_html("<h4 style='margin-bottom:0;'>iAM-Scout</h4>")
    render_html(
        f"<p style='margin-top:0; margin-bottom:0; font-size:12px; color:gray;'>{subtitle}</p>"
    )


def render_authors() -> None:
    """Render the author names on the right side of the header."""
    render_html(
        f"<p style='margin-top:22px; margin-bottom:0; text-align:right; font-size:12px; color:gray;'>{AUTHORS_TEXT}</p>"
    )


def render_separator() -> None:
    """Render a horizontal separator below the header."""
    render_html("<hr style='margin:8px 0;'>")


def render_header(page_title: str | None = None) -> None:
    """Render the shared application header."""
    logo_column, branding_column, authors_column = st.columns(HEADER_COLUMN_LAYOUT)

    with logo_column:
        render_logo()

    with branding_column:
        render_branding(page_title)

    with authors_column:
        render_authors()

    render_separator()
