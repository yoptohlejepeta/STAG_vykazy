import streamlit as st
import requests
import os
import datetime
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
    Přihlašte se pomocí <a
    href="{os.getenv("LOGIN_URL")}">Stagu</a></h2>""",
        unsafe_allow_html=True,
    )
else:
    idnos = st.text_input("Idno vyučujícího")
    col1, col2, col3 = st.columns(3)
    typ = col1.radio(
        "Časové období", ["Datum od do", "Podle semestru"] #"Aktuální měsíc" 
    )

    vars = {
        "vsechnyCasyKonani": True,
        "jenRozvrhoveAkce": False,
        "vsechnyAkce": True,
        "jenBudouciAkce": False,
        "lang": "cs",
        "outputFormat": "CSV",
        "rok": 2022,
        "outputFormatEncoding": "utf-8",
    }

    if typ == "Podle semestru":
        semestr = col2.selectbox(
            "Semestr",
            ["", "ZS", "LS"],
            help="Pokuď není specifikován, vrátí oba semestry.",
        )
        vars["semestr"] = semestr
        vars.pop("datumOd", None)
        vars.pop("datumDo", None)
    elif typ == "Datum od do":
        datum = col2.date_input(
            label="Datum",
            value=[datetime.date(2022, 9, 19), datetime.date(2023, 9, 30)],
            min_value=datetime.date(2022, 9, 19),
            max_value=datetime.date(2023, 9, 30),
        )
        try:
            vars["datumOd"] = datum[0].strftime("%d/%m/%Y").replace("/", ".")
            vars["datumDo"] = datum[1].strftime("%d/%m/%Y").replace("/", ".")
        except:
            pass
        vars.pop("semestr", None)


    if idnos:
        for idno in idnos.replace(" ", "").split(","):
            vars["ucitIdno"] = idno

            response = requests.get(
                data_url,
                cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
                params=vars,
            )
            data = response.text

            df = pd.read_csv(StringIO(data), sep=";")
            df = df.loc[
                (df.denZkr == "So")
                | (df.denZkr == "Ne")
                & (~df.datum.isin(czech_holidays))
            ]
            df = df.loc[df["obsazeni"] > 0]
            df.reset_index(inplace=True)
            df["hodinaSkutOd"] = pd.to_datetime(df["hodinaSkutOd"], format="%H:%M")
            df["hodinaSkutDo"] = pd.to_datetime(df["hodinaSkutDo"], format="%H:%M")
            df["pocetHodin"] = (
                df["hodinaSkutDo"] - df["hodinaSkutOd"]
            ).apply(lambda x: x.total_seconds()) / 3600
            df["hodinaSkutOd"] = df["hodinaSkutOd"].dt.strftime("%H:%M")
            df["hodinaSkutDo"] = df["hodinaSkutDo"].dt.strftime("%H:%M")
            st.subheader(df["jmeno.ucitel"][0] + " " + df["prijmeni.ucitel"][0] + " " + f"({idno})")
            df = df[
                [
                    "predmet",
                    "nazev",
                    "datum",
                    "obsazeni",
                    "pocetVyucHodin",
                    "pocetHodin",
                    "hodinaSkutOd",
                    "hodinaSkutDo",
                    "typAkceZkr",
                ]
            ]

            edited_df = st.experimental_data_editor(df, use_container_width=True, height= ((len(df)) + 1) * 35 + 3)
            st.metric("Počet hodin", sum(edited_df["pocetHodin"]))
