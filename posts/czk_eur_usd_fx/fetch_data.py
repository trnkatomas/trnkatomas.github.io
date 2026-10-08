"""Fetch CZK/EUR/USD exchange rate history.

Two independent sources so the CZK/EUR/USD triangle is made of three genuinely
independent quotes rather than one series derived from another:

- CNB (Czech National Bank): daily fixing, CZK per 1 EUR and CZK per 1 USD,
  published as one bulk text file per year.
- Frankfurter (ECB reference rates): USD per 1 EUR (the standard "EUR/USD"
  market quote), daily since 1999.

The window is pinned (START_DATE..END_DATE) so re-running the script reproduces
exactly the dataset the post's numbers were computed from. Move END_DATE forward
to refresh the data -- and then re-check the numbers quoted in the notebook text.

Run with the `data_modelling` conda env (has pandas/requests):
    /Users/tomastrnka/miniconda3/envs/data_modelling/bin/python fetch_data.py
"""
import io
import time

import pandas as pd
import requests

# Slovakia joined the euro on 2009-01-01; the window starts three years earlier.
START_DATE = "2006-01-01"
END_DATE = "2026-07-27"
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


def _in_window(df: pd.DataFrame) -> pd.DataFrame:
    mask = (df["date"] >= START_DATE) & (df["date"] <= END_DATE)
    return df[mask].sort_values("date").reset_index(drop=True)


def _check(df: pd.DataFrame, name: str) -> None:
    assert not df.isna().any().any(), f"{name}: missing values"
    assert not df["date"].duplicated().any(), f"{name}: duplicate dates"


def fetch_cnb() -> pd.DataFrame:
    frames = []
    for year in range(int(START_DATE[:4]), int(END_DATE[:4]) + 1):
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
    return _in_window(pd.concat(frames, ignore_index=True))


def fetch_frankfurter() -> pd.DataFrame:
    resp = requests.get(
        FRANKFURTER_URL.format(start=START_DATE, end=END_DATE),
        params={"from": "EUR", "to": "USD"},
        timeout=60,
    )
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
    # The API also returns the last rate *before* START_DATE; drop it.
    return _in_window(df)


def main() -> None:
    cnb = fetch_cnb()
    _check(cnb, "CNB")
    cnb.to_csv(f"{DATA_DIR}/cnb_czk_fixing.csv", index=False)
    print(f"CNB fixing rows: {len(cnb)}  range: {cnb['date'].min().date()} -> {cnb['date'].max().date()}")

    ecb = fetch_frankfurter()
    _check(ecb, "ECB")
    ecb.to_csv(f"{DATA_DIR}/ecb_eur_usd.csv", index=False)
    print(f"ECB USD/EUR rows: {len(ecb)}  range: {ecb['date'].min().date()} -> {ecb['date'].max().date()}")


if __name__ == "__main__":
    main()
