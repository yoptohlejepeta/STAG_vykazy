import streamlit as st
import pandas as pd
import requests
import datetime
from io import StringIO, BytesIO
import datetime


ucitel_url = "https://ws.ujep.cz/ws/services/rest2/ucitel/getUcitelInfo"


def get_month_days(year: int, month_name: str):
    month_names_czech = {
        "Leden": 1,
        "Únor": 2,
        "Březen": 3,
        "Duben": 4,
        "Květen": 5,
        "Červen": 6,
        "Červenec": 7,
        "Srpen": 8,
        "Září": 9,
        "Říjen": 10,
        "Listopad": 11,
        "Prosinec": 12,
    }

    month = month_names_czech.get(month_name)

    first_day = datetime.date(year, month, 1)
    next_month = first_day.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)

    return first_day.strftime("%d/%m/%Y").replace("/", "."), last_day.strftime(
        "%d/%m/%Y"
    ).replace("/", ".")


@st.cache_data(show_spinner=False, ttl=300)
def get_name(shortcut, department):
    url = "https://ws.ujep.cz/ws/services/rest2/predmety/getPredmetInfo"
    vars = {
        "zkratka": shortcut,
        "outputFormat": "CSV",
        "katedra": department,
        "outputFormatEncoding": "utf-8",
    }

    predmet = requests.get(
        url,
        cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
        params=vars,
    )

    data = predmet.text
    df = pd.read_csv(StringIO(data), sep=";")

    return df["nazev"][0]


@st.cache_data(show_spinner=False, ttl=300)
def get_tituly(titul_pred, titul_po, jmeno):
    if str(titul_pred) != "nan":
        jmeno = titul_pred + " " + jmeno
    if str(titul_po) != "nan":
        jmeno = jmeno + ", " + titul_po
    return jmeno


@st.cache_data(show_spinner=False, ttl=300)
def get_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        text = "Výkaz za sobotní, případně nedělní výuku v kombinovaném studiu"
        workbook = writer.book
        worksheet = workbook.add_worksheet()
        worksheet.merge_range("A1:D1", text)
        df.to_excel(writer, sheet_name="Sheet1", startrow=1, index=False)

    return buffer

@st.cache_data(show_spinner=False, ttl=300)
def get_vyucujici(idno):
    rozvrh = requests.get(
        ucitel_url,
        cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
        params={"ucitIdno": idno, "outputFormat": "CSV", "outputFormatEncoding": "utf-8"},
    )

    data = rozvrh.text
    df = pd.read_csv(StringIO(data), sep=";")
    jmeno = " ".join([df["jmeno"].iloc[0], df["prijmeni"].iloc[0]])
    jmeno_tituly = get_tituly(
        df["titulPred"].iloc[0], df["titulZa"].iloc[0], jmeno
    )
    
    return jmeno, jmeno_tituly



@st.cache_data(show_spinner=False, ttl=300)
def get_df(idno, url, holidays, vars, type):
    rozvrh = requests.get(
        url,
        cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
        params=vars,
    )

    data = rozvrh.text
    df = pd.read_csv(StringIO(data), sep=";")

    if df.empty:
        return df, None, None

    try:
        df.datum = pd.to_datetime(
            df.datum.apply(lambda x: x.replace(".", "/")), format="%d/%m/%Y"
        )
    except:
        pass
    df.sort_values(by=["datum", "hodinaSkutOd"], ascending=True, inplace=True)
    df.datum = df.datum.dt.strftime("%d/%m/%Y").apply(lambda x: x.replace("/", ". "))

    if type:
        df = df.loc[
            (df.denZkr == "So") | (df.denZkr == "Ne") & (~df.datum.isin(holidays))
        ]
    df = df.loc[df["obsazeni"] > 0]

    df.reset_index(inplace=True)

    df["typAkceZkr"].replace(
        {"Zápočet": "Zp", "Zkouška": "Zk", "Záp. před zk.": "Zpz"}, inplace=True
    )

    df["hodinaSkutOd"] = pd.to_datetime(df["hodinaSkutOd"], format="%H:%M")
    df["hodinaSkutDo"] = pd.to_datetime(df["hodinaSkutDo"], format="%H:%M")
    df["hodinaOdDo"] = (
        df["hodinaSkutOd"]
        .dt.strftime("%H:%M")
        .str.cat(df["hodinaSkutDo"].dt.strftime("%H:%M"), sep="–")
    )
    try:
        df["kodPredmetu"] = df["katedra"].str.cat(df["predmet"].astype("str"), sep="/")
    except:
        # Někde není vyplněna katedra. (např. idno: 2317, červen 2023)
        df["kodPredmetu"] = df["predmet"]

    df["pocetVyucHodin"] = (
        df["pocetVyucHodin"]
        .fillna(
            (df["hodinaSkutDo"] - df["hodinaSkutOd"]).apply(lambda x: x.total_seconds())
            / 3600
        )
        .round()
        .astype(int)
    )

    # U zápočtů a zkoušek je místo názvu přemětu pouze kód.
    for index, row in df.iterrows():
        if row["kodPredmetu"] == row["nazev"]:
            df.at[index, "nazev"] = get_name(row["predmet"], row["katedra"])

    df["akce"] = df["kodPredmetu"].str.cat(
        df["nazev"].str.cat(df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "),
        sep="  ",
    )

    try:
        for i in range(len(df)):
            row = df.iloc[i]
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

    return df
