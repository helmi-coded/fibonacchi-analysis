"""
fibonacci.py
------------
Reine Berechnungslogik fuer Fibonacci-Retracement-Level.
Haengt bewusst nicht von Streamlit oder yfinance ab, damit die
Funktionen isoliert testbar bleiben.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Klassische Fibonacci-Retracement-Verhaeltnisse. 78.6% gilt als Signal fuer
# eine vollstaendige bzw. fast vollstaendige Umkehr der vorherigen
# Kursbewegung und wird deshalb zusaetzlich zu den sechs Kernleveln gefuehrt.
FIBONACCI_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)

# Trendrichtung bestimmt, welche der beiden Standard-Formeln verwendet wird
# und wie 0 %/100 % zu interpretieren sind (siehe calculate_fibonacci_levels).
TREND_UP = "up"
TREND_DOWN = "down"


@dataclass(frozen=True)
class FibonacciResult:
    """Ergebnis der Fibonacci-Berechnung fuer eine konkrete Trendbewegung."""

    high: float
    low: float
    high_date: pd.Timestamp
    low_date: pd.Timestamp
    trend: str  # TREND_UP oder TREND_DOWN
    levels: dict[float, float]  # Ratio -> Kursniveau

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def trend_label(self) -> str:
        return "Aufwärtstrend" if self.trend == TREND_UP else "Abwärtstrend"

    def anchor_label(self, ratio: float) -> str:
        """
        Kurzer Zusatzhinweis fuer die Tabellen-/Chart-Beschriftung, was 0 %
        bzw. 100 % bei der gewaehlten Trendrichtung konkret bedeuten.
        """
        if ratio == 0.0:
            return " (Hoch)" if self.trend == TREND_UP else " (Tief)"
        if ratio == 1.0:
            return " (Tief)" if self.trend == TREND_UP else " (Hoch)"
        return ""

    def as_dataframe(self, currency: str = "") -> pd.DataFrame:
        """
        Fuer Tabellendarstellung in der UI.

        Parameters
        ----------
        currency: Original-Handelswaehrung des Tickers (z. B. "USD", "EUR").
            Wird hinter jedem Kurswert ausgegeben.
        """
        suffix = f" {currency}" if currency else ""
        df = pd.DataFrame(
            {
                "Level": [f"{ratio * 100:.1f}%{self.anchor_label(ratio)}" for ratio in self.levels],
                "Kurs": [f"{price:,.2f}{suffix}" for price in self.levels.values()],
            }
        )
        return df


def calculate_fibonacci_levels(df: pd.DataFrame, trend: str = TREND_UP) -> FibonacciResult:
    """
    Berechnet Hoch, Tief und die klassischen Fibonacci-Retracement-Level
    (0 %, 23,6 %, 38,2 %, 50 %, 61,8 %, 78,6 %, 100 %) fuer eine vom Nutzer
    identifizierte Trendbewegung (Swing High/Swing Low).

    Es werden je nach Trendrichtung zwei unterschiedliche Standardformeln
    verwendet:

        Aufwaertstrend (T -> H, trend=TREND_UP):
            level_price = high - (high - low) * ratio
            0 % = Hoch, 100 % = Tief (Retracement einer Aufwaertsbewegung
            nach unten in Richtung Tief).

        Abwaertstrend (H -> T, trend=TREND_DOWN):
            level_price = low + (high - low) * ratio
            0 % = Tief, 100 % = Hoch (Retracement einer Abwaertsbewegung
            nach oben in Richtung Hoch).

    Beide Formeln liefern dieselben sieben Kurswerte zwischen Hoch und Tief -
    lediglich die Zuordnung der Prozent-Label zur Richtung unterscheidet sich,
    passend zur jeweiligen Chartanalyse-Konvention.

    Parameters
    ----------
    df: DataFrame mit mindestens den Spalten "High" und "Low", bereits auf
        die vom Nutzer identifizierte Trendbewegung (Zeitfenster) zugeschnitten.
    trend: TREND_UP oder TREND_DOWN.

    Returns
    -------
    FibonacciResult mit Hoch, Tief, Trendrichtung und den berechneten Leveln.
    """
    if df.empty:
        raise ValueError("Leerer DataFrame: Fibonacci-Level koennen nicht berechnet werden.")

    if trend not in (TREND_UP, TREND_DOWN):
        raise ValueError(f"Ungueltige Trendrichtung: {trend!r}")

    high = float(np.max(df["High"]))
    low = float(np.min(df["Low"]))
    high_date = df["High"].idxmax()
    low_date = df["Low"].idxmin()

    price_range = high - low

    if trend == TREND_UP:
        levels = {ratio: high - price_range * ratio for ratio in FIBONACCI_RATIOS}
    else:
        levels = {ratio: low + price_range * ratio for ratio in FIBONACCI_RATIOS}

    return FibonacciResult(
        high=high,
        low=low,
        high_date=high_date,
        low_date=low_date,
        trend=trend,
        levels=levels,
    )
