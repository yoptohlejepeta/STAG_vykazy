import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv
import datetime
from io import StringIO
import datetime


def get_month_days(year, month_name):
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

    month = month_names_czech.get(month_name.lower())
    if month is None:
        return None, None

    first_day = datetime.date(year, month, 1)
    next_month = first_day.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)

    return first_day, last_day


@st.cache_data(show_spinner=False)
def get_df(idno, url, holidays, vars, rozsah):
    rozvrh = requests.get(
        url,
        cookies={"WSCOOKIE": st.session_state["stagUserTicket"][0]},
        params=vars,
    )

    data = rozvrh.text
    df = pd.read_csv(StringIO(data), sep=";")

    if df.empty:
        return df, None, None

    jmeno = df.loc[df.ucitIdno == idno]["jmeno.ucitel"].iloc[0]
    prijmeni = df.loc[df.ucitIdno == idno]["prijmeni.ucitel"].iloc[0]

    try:
        df.datum = pd.to_datetime(
            df.datum.apply(lambda x: x.replace(".", "/")), format="%d/%m/%Y"
        )
    except:
        pass
    df.sort_values(by=["datum", "hodinaSkutOd"], ascending=True, inplace=True)
    df.datum = df.datum.dt.strftime("%d/%m/%Y").apply(lambda x: x.replace("/", "."))

    if rozsah == "Víkendy + svátky":
        df = df.loc[
            (df.denZkr == "So") | (df.denZkr == "Ne") & (~df.datum.isin(holidays))
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

    df["kodPredmetu"] = df["katedra"].str.cat(df["predmet"].astype("str"), sep="/")
    df["pocetVyucHodin"] = (
        df["pocetVyucHodin"]
        .fillna(
            (df["hodinaSkutDo"] - df["hodinaSkutOd"]).apply(lambda x: x.total_seconds())
            / 3600
        )
        .round()
        .astype(int)
    )

    df["akce"] = df["kodPredmetu"].str.cat(
        df["nazev"].str.cat(df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "),
        sep="  ",
    )
    df.loc[df["kodPredmetu"] == df["nazev"], "akce"] = df["kodPredmetu"].str.cat(
        df["typAkceZkr"].apply(lambda x: f"({x})"), sep="  "
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

    return df, jmeno, prijmeni