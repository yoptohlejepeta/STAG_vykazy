import streamlit as st
import requests
import os
import pandas as pd
from io import StringIO
import holidays
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(layout="wide", page_title="STAG Výkazy", page_icon="📄")

st.title("Výkazy")

data_url = "https://ws.ujep.cz/ws/services/rest2/rozvrhy/getRozvrhByUcitel"
czech_holidays = holidays.CZ(years=2023)

if "stagUserTicket" not in st.session_state:
    ticket = st.experimental_get_query_params().get("stagUserTicket")
    st.session_state["stagUserTicket"] = ticket


if not st.session_state["stagUserTicket"]:
    st.write(
        f"""<h2>
    Přihlašte se pomocí <a target="_blank"
    href="{os.getenv("LOGIN_URL")}">Stagu</a></h2>""",
        unsafe_allow_html=True,
    )
else:
    idno = st.text_input("Idno vyučujícího")

if idno:
    vars = {
    "ucitIdno": idno,
    "semestr": "LS",
    "vsechnyCasyKonani": True,
    "jenRozvrhoveAkce": False,
    # "datumOd":"1.4.2023",
    # "datumDo":"30.4.2023",
    "vsechnyAkce": True,
    "jenBudouciAkce": False,
    "lang": "cs",
    "outputFormat": "CSV",
    "rok": 2022,
    "outputFormatEncoding": "utf-8",
}

    response = requests.get(data_url, cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]}, params=vars)
    data = response.text

    df = pd.read_csv(StringIO(data), sep=";")
    df = df.loc[
        (df.denZkr == "So") | (df.denZkr == "Ne") & (~df.datum.isin(czech_holidays))
    ]
    df.reset_index(inplace=True)
    df = df[
        [
            "predmet",
            "nazev",
            "datum",
            "obsazeni",
            "pocetVyucHodin",
            "hodinaSkutOd",
            "hodinaSkutDo",
            "typAkceZkr"
        ]
    ]

    edited_df = st.experimental_data_editor(df, use_container_width=True)