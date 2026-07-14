"""
data_fetcher.py
----------------
Zustaendig fuer den Abruf historischer Kursdaten via yfinance.
Enthaelt keine Berechnungs- oder UI-Logik (Separation of Concerns).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

# Konfiguration der in der UI wählbaren Zeitraeume.
# Zwei Modi:
#   "calendar" -> Zeitraum = heute minus N Kalendertage (einfache Rueckschau).
#   "trading"  -> Zeitraum = exakt die letzten N Handelstage (Boersentage).
#
# Der "200 Handelstage (GD 200)"-Zeitraum bildet bewusst den klassischen
# 200-Tage-Durchschnitt (GD 200) nach: Dieser bezieht sich per Definition auf
# 200 Handelstage, NICHT auf 200 Kalendertage. Bei reiner Kalendertage-Rechnung
# (heute − 200 Tage) waeren wegen Wochenenden/Feiertagen nur ca. 140-145
# tatsaechliche Handelstage enthalten - das wuerde Hoch/Tief und damit die
# Fibonacci-Level verfaelschen.
PERIOD_CONFIG: dict[str, dict] = {
    "1 Monat": {"mode": "calendar", "count": 30},
    "200 Handelstage (GD 200)": {"mode": "trading", "count": 200},
    "1 Jahr": {"mode": "calendar", "count": 365},
    "5 Jahre": {"mode": "calendar", "count": 365 * 5},
}


class DataFetchError(Exception):
    """Wird ausgeloest, wenn fuer ein Ticker-Symbol keine Daten verfuegbar sind."""


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_price_history(ticker: str, period_label: str) -> pd.DataFrame:
    """
    Laedt historische Tageskurse (OHLC) fuer ein Ticker-Symbol.

    Parameters
    ----------
    ticker: Ticker-Symbol, z. B. "AAPL", "SAP.DE".
    period_label: Einer der Schluessel aus PERIOD_CONFIG.

    Returns
    -------
    DataFrame mit Spalten Open, High, Low, Close, Volume, indiziert nach Datum.
    Im Modus "trading" enthaelt das Ergebnis maximal genau `count` Zeilen
    (die letzten N Handelstage); bei sehr jungen Tickern koennen es weniger
    sein, falls insgesamt weniger Handelstage existieren.

    Raises
    ------
    DataFetchError, falls keine Daten gefunden wurden (z. B. ungueltiges Ticker-Symbol).
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise DataFetchError("Bitte ein Ticker-Symbol eingeben.")

    config = PERIOD_CONFIG.get(period_label)
    if config is None:
        raise DataFetchError(f"Unbekannter Zeitraum: {period_label}")

    mode = config["mode"]
    count = config["count"]
    end_date = datetime.now()

    if mode == "trading":
        # Kalendertage-Puffer fuer die Handelstage-Abfrage: Handelstage machen
        # nur ca. 5/7 der Kalendertage aus (Faktor 1.6), zzgl. fixem Puffer fuer
        # Feiertage, damit sicher genuegend Handelstage geladen werden.
        buffer_days = int(count * 1.6) + 30
        start_date = end_date - timedelta(days=buffer_days)
    else:
        start_date = end_date - timedelta(days=count)

    try:
        raw = yf.Ticker(ticker).history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
        )
    except Exception as exc:  # yfinance kann diverse Exceptions werfen
        raise DataFetchError(f"Fehler beim Abruf von '{ticker}': {exc}") from exc

    if raw is None or raw.empty:
        raise DataFetchError(
            f"Keine Kursdaten fuer '{ticker}' gefunden. Bitte Ticker-Symbol pruefen."
        )

    # Defensive Bereinigung: manche yfinance-Versionen liefern je nach
    # Aufrufkontext MultiIndex-Spalten (z. B. ("Open", "AAPL")) - flach machen,
    # falls vorhanden, damit df["Open"] etc. zuverlaessig funktioniert.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close"]
    raw = raw.dropna(subset=required_cols)

    # Duplikate/unsortierte Zeitstempel koennen bei manchen Tickern auftreten
    # (z. B. durch nachtraeglich korrigierte Datenpunkte) und sollten vor der
    # Chart-Erstellung bereinigt werden.
    raw = raw[~raw.index.duplicated(keep="last")].sort_index()

    # Zeitzonen-Info entfernen: ein tz-aware Index ist fuer die Berechnung
    # nicht relevant und kann bei der Serialisierung fuer Plotly/Streamlit
    # in seltenen Faellen zu Problemen fuehren.
    if raw.index.tz is not None:
        raw.index = raw.index.tz_localize(None)

    # OHLC-Spalten explizit als natives float64 casten (statt z. B. pandas'
    # nullable "Float64"-Extension-Dtype), um Kompatibilitaetsprobleme mit
    # Plotly bei der Trace-Erstellung auszuschliessen.
    for col in required_cols:
        raw[col] = raw[col].astype("float64")

    if mode == "trading":
        # Auf exakt die letzten `count` Handelstage zuschneiden (falls durch
        # den Kalenderpuffer mehr geladen wurden als benoetigt).
        raw = raw.tail(count)

    raw.index.name = "Date"
    return raw


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_ticker_meta(ticker: str) -> dict[str, str]:
    """
    Ermittelt Firmenname und Original-Handelswaehrung zum Ticker.

    Wichtig: Es wird bewusst IMMER die Original-Waehrung des Tickers
    zurueckgegeben (z. B. USD fuer AAPL, EUR fuer SAP.DE) - keine
    Umrechnung in Euro. Kurse werden in der App stets zusammen mit
    dieser Waehrung dargestellt.

    Returns
    -------
    dict mit den Schluesseln "name" und "currency" (Fallback: "" bzw. "N/A").
    """
    ticker = ticker.strip().upper()
    name = ticker
    currency = "N/A"

    try:
        yf_ticker = yf.Ticker(ticker)
        # fast_info ist deutlich schneller/robuster als .info fuer die Waehrung.
        fast_currency = getattr(yf_ticker, "fast_info", {}).get("currency")
        if fast_currency:
            currency = fast_currency

        info = yf_ticker.info
        name = info.get("longName") or info.get("shortName") or ticker
        if currency == "N/A":
            currency = info.get("currency", "N/A")
    except Exception:
        pass

    return {"name": name, "currency": currency}
