import streamlit as st
import os
import datetime
import holidays
from dotenv import load_dotenv

from utils import get_df
from utils import get_excel
from utils import get_month_days

load_dotenv()


st.set_page_config(layout="wide", page_title="STAG Výkazy", page_icon="📄")
st.title("STAG Výkazy")


# Dodatečné CSS
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

hover_css = """
    <style>
        a span:hover {
            color: #FF4B4B;
        }
    </style>
    """

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """

st.markdown(hide_streamlit_style, unsafe_allow_html=True)
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


# Proměnné
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

mesice = [
    "Leden",
    "Únor",
    "Březen",
    "Duben",
    "Květen",
    "Červen",
    "Červenec",
    "Srpen",
    "Září",
    "Říjen",
    "Listopad",
    "Prosinec",
]

# Výběr parametrů
# Ticket z headeru
if "stagUserTicket" not in st.session_state:
    ticket = st.experimental_get_query_params().get("stagUserTicket")
    st.session_state["stagUserTicket"] = ticket

# Pokud není ticket -> login stránka
if not st.session_state["stagUserTicket"] or st.session_state["stagUserTicket"][0] == "anonymous":
    idnos = None
    login_url = os.getenv("LOGIN_URL")
    st.header(f"Přihlašte se pomocí [Stagu]({login_url})")
else:
    idnos = st.text_input(
        "Idno vyučujícího", placeholder="Zadejte Idno vyučujících oddělené čárkami"
    )
    col1, col2, col3 = st.columns(3)
    # rozsah = col1.radio("Rozsah výkazů", ["Víkendy + svátky", "Všechny dny"])
    vikendy = col1.toggle(
        "Víkendy + svátky",
        value=True,
        help="Zobrazí pouze víkendy a svátky. Pokud je vypnuto, zobrazí všechny dny.",
    )
    typ = col2.radio("Časové období", ["Podle měsíce", "Datum od do"])

    if typ == "Datum od do":
        datum = col3.date_input(
            label="Datum",
            value=[datetime.date.today(), datetime.date.today()],
        )
        try:
            vars["datumOd"] = datum[0].strftime("%d/%m/%Y").replace("/", ".")
            vars["datumDo"] = datum[1].strftime("%d/%m/%Y").replace("/", ".")
        except:
            pass
        vars.pop("semestr", None)
    elif typ == "Podle měsíce":
        mesic = col3.selectbox("Měsíc", mesice)
        rok = col3.selectbox("Rok", [datetime.datetime.now().year - i for i in range(3)])
        # vars["datumOd"] = mesice.get(mesic)[0].strftime("%d/%m/%Y").replace("/", ".")
        # vars["datumDo"] = mesice.get(mesic)[1].strftime("%d/%m/%Y").replace("/", ".")
        vars["datumOd"], vars["datumDo"] = get_month_days(year=rok, month_name=mesic)


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

        df, jmeno, jmeno_tituly = get_df(
            idno, rozvrh_url, czech_holidays, vars, vikendy
        )

        if jmeno == None:
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            continue

        # Tabulka
        # Přejmenování sloupců kvůli výstupu
        df = df[["datum", "hodinaOdDo", "pocetVyucHodin", "akce"]]
        df.columns = ["Datum", "Hodina od do", "Počet hodin", "Akce"]

        hodiny_pocet = sum(df["Počet hodin"].fillna(0))

        if hodiny_pocet == 0:
            st.markdown(
                f"<h3> <text style= color:grey;>{jmeno_tituly}</text> ({idno}) <a id='{idno}'/></h3>",
                unsafe_allow_html=True,
            )
            with st.sidebar:
                st.markdown(
                    f"<a href = #{idno} style='color: grey; text-decoration: none; font-size: 1.5em;'><span style='transition: color 0.3s;'><s>{jmeno}</s> ({idno})</span></a>",
                    unsafe_allow_html=True,
                )
                st.markdown(custom_divider, unsafe_allow_html=True)
        else:
            st.subheader(f"{jmeno_tituly} ({idno})", anchor=f"{idno}")
            with st.sidebar:
                st.markdown(
                    f"<a href = #{idno} style='color: inherit; text-decoration: none; font-size: 1.5em;'><span style='transition: color 0.3s;'>{jmeno} ({idno})</span></a>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="custom-divider"></div>', unsafe_allow_html=True
                )

        st.table(df)

        # Část pod tabulkou
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
