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

# Zuordnung der in der UI wählbaren Zeitraeume auf Kalendertage.
# yfinance kennt keinen nativen "200 Tage"-Zeitraum, daher wird
# grundsaetzlich ueber ein Start-/Enddatum gearbeitet (robuster als
# die period="..."-Kurzschreibweise von yfinance).
PERIOD_TO_DAYS: dict[str, int] = {
    "1 Monat": 30,
    "200 Tage": 200,
    "1 Jahr": 365,
    "5 Jahre": 365 * 5,
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
    period_label: Einer der Schluessel aus PERIOD_TO_DAYS.

    Returns
    -------
    DataFrame mit Spalten Open, High, Low, Close, Volume, indiziert nach Datum.

    Raises
    ------
    DataFetchError, falls keine Daten gefunden wurden (z. B. ungueltiges Ticker-Symbol).
    """
    ticker = ticker.strip().upper()
    if not ticker:
        raise DataFetchError("Bitte ein Ticker-Symbol eingeben.")

    days = PERIOD_TO_DAYS.get(period_label)
    if days is None:
        raise DataFetchError(f"Unbekannter Zeitraum: {period_label}")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

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

    raw = raw.dropna(subset=["Open", "High", "Low", "Close"])
    raw.index.name = "Date"
    return raw


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_company_name(ticker: str) -> str:
    """Bester Versuch, den Firmennamen zum Ticker zu ermitteln (fuer Chart-Titel)."""
    try:
        info = yf.Ticker(ticker.strip().upper()).info
        return info.get("longName") or info.get("shortName") or ticker.upper()
    except Exception:
        return ticker.upper()
