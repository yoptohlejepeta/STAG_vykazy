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

st.title("STAG Výkazy")

data_url = "https://ws.ujep.cz/ws/services/rest2/rozvrhy/getRozvrhByUcitel"
czech_holidays = holidays.CZ(years=2023)

if "stagUserTicket" not in st.session_state:
    ticket = st.experimental_get_query_params().get("stagUserTicket")
    st.session_state["stagUserTicket"] = ticket


if not st.session_state["stagUserTicket"]:
    idnos = None
    st.write(
        f"""<h2>
    Přihlašte se pomocí <a
    href="{os.getenv("LOGIN_URL")}">Stagu</a></h2>""",
        unsafe_allow_html=True,
    )
else:
    idnos = st.text_input(
        "Idno vyučujícího", help="Zadejte Idno vyučujících oddělené čárkami."
    )
    col1, col2, col3 = st.columns(3)
    typ = col1.radio(
        "Časové období", ["Datum od do", "Podle semestru"]  # "Aktuální měsíc"
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
        if df.empty:
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            continue

        jmeno = df["jmeno.ucitel"][0]
        prijmeni = df["prijmeni.ucitel"][0]

        df = df.loc[
            (df.denZkr == "So") | (df.denZkr == "Ne") & (~df.datum.isin(czech_holidays))
        ]
        df = df.loc[df["obsazeni"] > 0]
        df.reset_index(inplace=True)
        df["hodinaSkutOd"] = pd.to_datetime(df["hodinaSkutOd"], format="%H:%M")
        df["hodinaSkutDo"] = pd.to_datetime(df["hodinaSkutDo"], format="%H:%M")
        df["hodinaOdDo"] = (
            df["hodinaSkutOd"]
            .dt.strftime("%H:%M")
            .str.cat(df["hodinaSkutDo"].dt.strftime("%H:%M"), sep="—")
        )
        df["kodPredmetu"] = df["katedra"] + "/" + df["predmet"]
        df["pocetVyucHodin"] = df["pocetVyucHodin"].fillna(
            (df["hodinaSkutDo"] - df["hodinaSkutOd"]).apply(lambda x: x.total_seconds())
            / 3600
        )

        df["akce"] = df["kodPredmetu"].str.cat(
            df["nazev"].str.cat(df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "),
            sep="  ",
        )

        st.subheader(f"{jmeno} {prijmeni} ({idno})")

        df = df[["datum", "hodinaOdDo", "pocetVyucHodin", "akce"]]

        try:
            for i in range(len(df)):
                row = df.iloc[i]
                # for j in range(i + 1, len(df)):
                next_row = df.iloc[i + 1]
                while (row["datum"] == next_row["datum"]) and (
                    row["hodinaOdDo"] == next_row["hodinaOdDo"]
                ):
                    df.iloc[i, df.columns.get_loc("akce")] = " + ".join(
                        [row["akce"], next_row["akce"]]
                    )
                    df.drop(labels=i + 1, inplace=True)
                    df.reset_index(inplace=True, drop=True)
                    next_row = df.iloc[i + 1]
                    row = df.iloc[i]
        except IndexError:
            pass

        edited_df = st.experimental_data_editor(
            df,
            use_container_width=True,
            height=((len(df)) + 2) * 35 + 3,
            num_rows="dynamic",
        )
        # st.download_button(
        #     label="Stáhnout CSV",
        #     data=edited_data,
        #     file_name="data.csv",
        #     mime='text/csv',
        # )
        st.metric("Počet hodin", int(sum(edited_df["pocetVyucHodin"].fillna(0))))
