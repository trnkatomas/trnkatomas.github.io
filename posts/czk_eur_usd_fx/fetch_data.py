"""Fetch CZK/EUR/USD exchange rate history.

Two independent sources so the CZK/EUR/USD triangle is made of three genuinely
independent quotes rather than one series derived from another:

- CNB (Czech National Bank): daily fixing, CZK per 1 EUR and CZK per 1 USD,
  published as one bulk text file per year.
- Frankfurter (ECB reference rates): EUR per 1 USD, daily since 1999.

Run with the `data_modelling` conda env (has pandas/requests):
    /Users/tomastrnka/miniconda3/envs/data_modelling/bin/python fetch_data.py
"""
import datetime as dt
import io
import time

import pandas as pd
import requests

START_YEAR = 2006
END_YEAR = dt.date.today().year
DATA_DIR = "data"

CNB_URL = (
    "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/"
    "kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/rok.txt"
)
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/{start}..{end}"


def _split_blocks(text: str) -> list[str]:
    # CNB restarts the header line whenever the currency list changes mid-year
    # (e.g. 2009: Slovakia joins the euro; 2022: RUB dropped). Split into blocks
    # at each header so every block can be parsed with its own column set.
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("Datum|")]
    starts.append(len(lines))
    return ["\n".join(lines[starts[i]:starts[i + 1]]) for i in range(len(starts) - 1)]


def fetch_cnb() -> pd.DataFrame:
    frames = []
    for year in range(START_YEAR, END_YEAR + 1):
        resp = requests.get(CNB_URL, params={"rok": year}, timeout=30)
        resp.raise_for_status()
        for block in _split_blocks(resp.text):
            df = pd.read_csv(io.StringIO(block), sep="|", decimal=",")
            df = df[["Datum", "1 EUR", "1 USD"]].rename(
                columns={"Datum": "date", "1 EUR": "czk_per_eur", "1 USD": "czk_per_usd"}
            )
            df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
            frames.append(df)
        time.sleep(0.2)  # be polite to cnb.cz
    out = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    return out


def fetch_frankfurter(start: str, end: str) -> pd.DataFrame:
    resp = requests.get(FRANKFURTER_URL.format(start=start, end=end), params={"from": "EUR", "to": "USD"}, timeout=60)
    resp.raise_for_status()
    rates = resp.json()["rates"]
    # Frankfurter's from=EUR&to=USD returns USD per 1 EUR -- the standard "EURUSD" market
    # quote convention. Name it explicitly so it isn't mixed up with a CZK-style "per EUR"
    # or "per USD" column further down the pipeline.
    df = pd.DataFrame(
        [(date, vals["USD"]) for date, vals in rates.items()],
        columns=["date", "usd_per_eur"],
    )
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def main() -> None:
    cnb = fetch_cnb()
    cnb.to_csv(f"{DATA_DIR}/cnb_czk_fixing.csv", index=False)
    print(f"CNB fixing rows: {len(cnb)}  range: {cnb['date'].min().date()} -> {cnb['date'].max().date()}")

    start = f"{START_YEAR}-01-01"
    end = dt.date.today().isoformat()
    ecb = fetch_frankfurter(start, end)
    ecb.to_csv(f"{DATA_DIR}/ecb_eur_usd.csv", index=False)
    print(f"ECB USD/EUR rows: {len(ecb)}  range: {ecb['date'].min().date()} -> {ecb['date'].max().date()}")


if __name__ == "__main__":
    main()
