import os
import pandas as pd
import requests

# Data set éCO2mix national (RTE), found on data.gouv.fr / ODRÉ
URL = ("https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
       "eco2mix-national-cons-def/exports/csv?delimiter=%3B")
FILE = "data/eco2mix.csv"

#Giving the months their seasons.
SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
           5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer",
           9: "Autumn", 10: "Autumn", 11: "Autumn"}

#Downloading the dataset
def download():
    if not os.path.exists(FILE):
        os.makedirs("data", exist_ok=True)
        rep = requests.get(URL, timeout=300)
        rep.raise_for_status()
        with open(FILE, "wb") as f:
            f.write(rep.content)

#Loading the data and cleaning it using pandas, returning a DataFrame and a quality report.
def load():
    download()
    raw = pd.read_csv(FILE, sep=";")

    # Checking data for problems
    report = {
        "ligns": len(raw),
        "missing_co2": int(raw["taux_co2"].isna().sum()),
        "duplicates": int(raw.duplicated(subset=["date_heure"]).sum()),
        "weird_values": int(((raw["taux_co2"] < 0) | (raw["taux_co2"] > 1000)).sum()),
    }

    # Cleaning the data by removing duplicates, missing values, and weird values, and adding new columns for hour, month, year, season, and weekend.
    df = raw.drop_duplicates(subset=["date_heure"]).dropna(subset=["taux_co2"])
    df = df[(df["taux_co2"] >= 0) & (df["taux_co2"] <= 1000)].copy()

    t = pd.to_datetime(df["date_heure"], utc=True).dt.tz_convert("Europe/Paris")
    df["hour"] = t.dt.hour
    df["month"] = t.dt.month
    df["year"] = t.dt.year
    df["season"] = df["month"].map(SEASONS)
    df["weekend"] = t.dt.dayofweek >= 5
    report["lignes_gardees"] = len(df)
    return df[["taux_co2", "hour", "month", "year", "season", "weekend"]], report
