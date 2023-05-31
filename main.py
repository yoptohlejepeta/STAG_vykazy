import streamlit as st
import requests
import os
import datetime
import pandas as pd
from io import StringIO, BytesIO
import holidays
from dotenv import load_dotenv

from utils import get_df
from utils import get_excel

load_dotenv()


st.set_page_config(layout="wide", page_title="STAG Výkazy", page_icon="📄")
st.title("STAG Výkazy")


# Dodatečné CSS
# -----------------------------
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

hover_css = """
    <style>
        a span:hover {
            color: #FF4B4B; /* Replace with your desired hover color */
        }
    </style>
    """

st.markdown(hide_table_row_index, unsafe_allow_html=True)
st.markdown(hover_css, unsafe_allow_html=True)

# Vlastní divider. st.divider kolem sebe dělá moc velké mezery
st.markdown(
    """
    <style>
    .custom-divider {
        width: 100%;
        height: 1px;
        background-color: #bbb;
        margin-top: -5px;
        margin-bottom: -5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
custom_divider = '<div class="custom-divider"></div>'
# -----------------------------


# Proměnné
# -----------------------------
rozvrh_url = "https://ws.ujep.cz/ws/services/rest2/rozvrhy/getRozvrhByUcitel"
ucitel_url = "https://ws.ujep.cz/ws/services/rest2/ucitel/getUcitelInfo"
czech_holidays = holidays.CZ(years=2023)
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
mesice = {
    "Leden": [datetime.date(2023, 1, 1), datetime.date(2023, 1, 31)],
    "Únor": [datetime.date(2023, 2, 1), datetime.date(2023, 2, 28)],
    "Březen": [datetime.date(2023, 3, 1), datetime.date(2023, 3, 31)],
    "Duben": [datetime.date(2023, 4, 1), datetime.date(2023, 4, 30)],
    "Květen": [datetime.date(2023, 5, 1), datetime.date(2023, 5, 31)],
    "Červen": [datetime.date(2023, 6, 1), datetime.date(2023, 6, 30)],
    "Červenec": [datetime.date(2023, 7, 1), datetime.date(2023, 7, 31)],
    "Srpen": [datetime.date(2023, 8, 1), datetime.date(2023, 8, 31)],
    "Září": [datetime.date(2022, 9, 1), datetime.date(2022, 9, 30)],
    "Říjen": [datetime.date(2022, 10, 1), datetime.date(2022, 10, 31)],
    "Listopad": [datetime.date(2022, 11, 1), datetime.date(2022, 11, 30)],
    "Prosinec": [datetime.date(2022, 12, 1), datetime.date(2022, 12, 31)],
}
# -----------------------------

# Výběr parametrů
# -----------------------------
# Ticket z headeru
if "stagUserTicket" not in st.session_state:
    ticket = st.experimental_get_query_params().get("stagUserTicket")
    st.session_state["stagUserTicket"] = ticket

# Pokud není tiket -> login stránka
if not st.session_state["stagUserTicket"]:
    idnos = None
    login_url = os.getenv("LOGIN_URL")
    st.header(f"Přihlašte se pomocí [Stagu]({login_url})")
else:
    idnos = st.text_input(
        "Idno vyučujícího", placeholder="Zadejte Idno vyučujících oddělené čárkami"
    )
    col1, col2, col3 = st.columns(3)
    rozsah = col1.radio("Rozsah výkazů", ["Víkendy + svátky", "Všechny dny"])
    typ = col2.radio("Časové období", ["Podle měsíce", "Datum od do"])

    if typ == "Datum od do":
        datum = col3.date_input(
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
    elif typ == "Podle měsíce":
        mesic = col3.selectbox("Měsíc", mesice.keys())
        vars["datumOd"] = mesice.get(mesic)[0].strftime("%d/%m/%Y").replace("/", ".")
        vars["datumDo"] = mesice.get(mesic)[1].strftime("%d/%m/%Y").replace("/", ".")
# -----------------------------


if idnos:
    with st.sidebar:
        st.markdown(
            "<h2 style='font-size: 1.5em;'>Vyučující:</h2>", unsafe_allow_html=True
        )

    for idno in list(dict.fromkeys(idnos.replace(" ", "").split(","))):
        try:
            idno = int(idno)
            vars["ucitIdno"] = idno
        except:
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            with st.sidebar:
                st.markdown(
                    f"<a href = #{idno} style='color: grey; text-decoration: none; font-size: 1.5em;'><span style='transition: color 0.3s;'>?{idno}?</span></a>",
                    unsafe_allow_html=True,
                )
                st.markdown(custom_divider, unsafe_allow_html=True)
            continue

        df, jmeno = get_df(idno, rozvrh_url, czech_holidays, vars, rozsah)

        if jmeno == None:
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            continue

        # Tabulka
        # -----------------------------
        # Přejmenování sloupců kvůli výstupu
        df = df[["datum", "hodinaOdDo", "pocetVyucHodin", "akce"]]
        df.columns = ["Datum", "Hodina od do", "Počet hodin", "Akce"]

        hodiny_pocet = sum(df["Počet hodin"].fillna(0))

        if hodiny_pocet == 0:
            st.markdown(
                f"<h3> <text style= color:grey;>{jmeno}</text> ({idno}) <a id='{idno}'/></h3>",
                unsafe_allow_html=True,
            )
            with st.sidebar:
                st.markdown(
                    f"<a href = #{idno} style='color: grey; text-decoration: none; font-size: 1.5em;'><span style='transition: color 0.3s;'><s>{jmeno}</s> ({idno})</span></a>",
                    unsafe_allow_html=True,
                )
                st.markdown(custom_divider, unsafe_allow_html=True)
        else:
            st.subheader(f"{jmeno} ({idno})", anchor=f"{idno}")
            with st.sidebar:
                st.markdown(
                    f"<a href = #{idno} style='color: inherit; text-decoration: none; font-size: 1.5em;'><span style='transition: color 0.3s;'>{jmeno} ({idno})</span></a>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="custom-divider"></div>', unsafe_allow_html=True
                )

        st.table(df)
        # -----------------------------

        # Část pod tabulkou
        # -----------------------------
        col1, col2, col3 = st.columns([9, 1, 1])
        col1.metric("Celkem hodin", hodiny_pocet)

        col2.download_button(
            label="📥 Excel",
            data=get_excel(df),
            file_name=f"vykaz-{jmeno}-{idno}.xlsx",
            mime="application/vnd.ms-excel",
        )

        col3.download_button(
            label="📥 CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"vykaz-{jmeno}-{idno}.csv",
            mime="text/csv",
        )
