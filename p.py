import streamlit as st
import requests
import os
import datetime
import pandas as pd
from io import StringIO, BytesIO
import holidays
from dotenv import load_dotenv
import polars as pl

load_dotenv()


st.set_page_config(layout="wide", page_title="STAG Výkazy", page_icon="📄")

hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

st.markdown(hide_table_row_index, unsafe_allow_html=True)

st.title("STAG Výkazy")

rozvrh_url = "https://ws.ujep.cz/ws/services/rest2/rozvrhy/getRozvrhByUcitel"
ucitel_url = "https://ws.ujep.cz/ws/services/rest2/ucitel/getUcitelInfo"
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
        "Idno vyučujícího", placeholder="Zadejte Idno vyučujících oddělené čárkami"
    )
    col1, col2, col3 = st.columns(3)
    typ = col1.radio("Časové období", ["Podle měsíce", "Datum od do"]) # "Podle semestru"

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
    elif typ == "Podle měsíce":
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
        mesic = col2.selectbox("Měsíc", mesice.keys())
        vars["datumOd"] = mesice.get(mesic)[0].strftime("%d/%m/%Y").replace("/", ".")
        vars["datumDo"] = mesice.get(mesic)[1].strftime("%d/%m/%Y").replace("/", ".")
        vars.pop("semestr", None)


if idnos:
    for idno in list(dict.fromkeys(idnos.replace(" ", "").split(","))): # ???
        try:
            vars["ucitIdno"] = int(idno)
        except:
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            continue

        rozvrh = requests.get(
            rozvrh_url,
            cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
            params=vars,
        )

        data = rozvrh.text

        df = pl.read_csv(StringIO(data), separator=";")
        if df.is_empty():
            st.subheader(idno)
            st.write("Zkontrolujte, že jste správně zadali Idno vyučujícího.")
            continue

        jmeno = df.filter(pl.col("ucitIdno").cast(str) == idno).select("jmeno.ucitel").item(0,0)
        prijmeni = df.filter(pl.col("ucitIdno").cast(str) == idno).select("prijmeni.ucitel").item(0,0)
        df.with_columns(
            pl.col("datum").apply(lambda x: x.replace(".", "/")).str.to_datetime("%d/%m/%Y")
        ).sort(["datum", "hodinaSkutOd"], descending=False)
        st.write(df.inf)
        # df.datum = df.datum.dt.strftime("%d/%m/%Y").apply(lambda x: x.replace("/", "."))
        st.dataframe(df.to_pandas())
        # df = df.loc[
        #     (df.denZkr == "So") | (df.denZkr == "Ne") & (~df.datum.isin(czech_holidays))
        # ]
        # df = df.loc[df["obsazeni"] > 0]

        # df.reset_index(inplace=True)

        # df["hodinaSkutOd"] = pd.to_datetime(df["hodinaSkutOd"], format="%H:%M")
        # df["hodinaSkutDo"] = pd.to_datetime(df["hodinaSkutDo"], format="%H:%M")
        # df["hodinaOdDo"] = (
        #     df["hodinaSkutOd"]
        #     .dt.strftime("%H:%M")
        #     .str.cat(df["hodinaSkutDo"].dt.strftime("%H:%M"), sep="—")
        # )

        # df["kodPredmetu"] = df["katedra"].str.cat(df["predmet"], sep = "/")
        # df["pocetVyucHodin"] = df["pocetVyucHodin"].fillna(
        #     (df["hodinaSkutDo"] - df["hodinaSkutOd"]).apply(lambda x: x.total_seconds())
        #     / 3600
        # ).round().astype(int)

        # df["akce"] = df["kodPredmetu"].str.cat(
        #     df["nazev"].str.cat(df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "),
        #     sep="  ",
        # )
        # df.loc[df["kodPredmetu"] == df["nazev"], "akce"] = df["kodPredmetu"].str.cat(
        #     df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "
        # )

        # hodiny_pocet = sum(df["pocetVyucHodin"].fillna(0))

        # if hodiny_pocet == 0:
        #     # st.subheader(f":blue[{jmeno} {prijmeni}] ({idno})")
        #     st.markdown(f"<h3> <text style= color:grey;>{jmeno} {prijmeni}</text> ({idno}) </h3>", unsafe_allow_html=True)
        # else:
        #     st.subheader(f"{jmeno} {prijmeni} ({idno})")

        # df = df[["datum", "hodinaOdDo", "pocetVyucHodin", "akce"]]

        # try:
        #     for i in range(len(df)):
        #         row = df.iloc[i]
        #         next_row = df.iloc[i + 1]
        #         while (row["datum"] == next_row["datum"]) and (
        #             row["hodinaOdDo"] == next_row["hodinaOdDo"]
        #         ):
        #             df.iloc[i, df.columns.get_loc("akce")] = " + ".join(
        #                 [row["akce"], next_row["akce"]]
        #             )
        #             df.drop(labels=i + 1, inplace=True)
        #             df.reset_index(inplace=True, drop=True)
        #             next_row = df.iloc[i + 1]
        #             row = df.iloc[i]
        # except IndexError:
        #     pass

        # df.columns = ["Datum", "Hodina od do", "Počet hodin", "Akce"]

        # # edited_df = st.experimental_data_editor(
        # #     df,
        # #     use_container_width=True,
        # #     height=((len(df)) + 2) * 35 + 3,
        # #     num_rows="dynamic",
        # # )
        # st.table(df)

        # col1, col2 = st.columns([9, 1])

        # col1.metric("Celkem hodin", hodiny_pocet)

        # buffer = BytesIO()
        # with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        #     df.to_excel(writer, sheet_name="Sheet1", index=False)
        #     writer.save()

        #     col2.download_button(
        #         label="Stáhnout Excel",
        #         data=buffer,
        #         file_name=f"vykaz-{jmeno}-{prijmeni}-{idno}.xlsx",
        #         mime="application/vnd.ms-excel",
        #     )

        # col2.download_button(
        #     label="Stáhnout CSV",
        #     data=df.to_csv(index=False).encode("utf-8"),
        #     file_name=f"vykaz-{jmeno}-{prijmeni}-{idno}.csv",
        #     mime="text/csv",
        # )
