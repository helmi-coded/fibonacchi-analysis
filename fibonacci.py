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

# Klassische Fibonacci-Retracement-Verhaeltnisse.
FIBONACCI_RATIOS: tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 1.0)


@dataclass(frozen=True)
class FibonacciResult:
    """Ergebnis der Fibonacci-Berechnung fuer einen Kurszeitraum."""

    high: float
    low: float
    high_date: pd.Timestamp
    low_date: pd.Timestamp
    levels: dict[float, float]  # Ratio -> Kursniveau

    @property
    def range(self) -> float:
        return self.high - self.low

    def as_dataframe(self) -> pd.DataFrame:
        """Fuer Tabellendarstellung in der UI."""
        df = pd.DataFrame(
            {
                "Level": [f"{ratio * 100:.1f}%" for ratio in self.levels],
                "Kurs": list(self.levels.values()),
            }
        )
        return df


def calculate_fibonacci_levels(df: pd.DataFrame) -> FibonacciResult:
    """
    Berechnet Hoch, Tief und die klassischen Fibonacci-Retracement-Level
    (0%, 23.6%, 38.2%, 50%, 61.8%, 100%) fuer den uebergebenen Zeitraum.

    Die Level werden nach der Standardformel fuer eine Aufwaertsbewegung
    (Retracement von einem Hoch zurueck in Richtung Tief) berechnet:

        level_price = high - (high - low) * ratio

    D. h. 0% entspricht dem Hoch, 100% entspricht dem Tief.

    Parameters
    ----------
    df: DataFrame mit mindestens den Spalten "High" und "Low".

    Returns
    -------
    FibonacciResult mit Hoch, Tief und den berechneten Leveln.
    """
    if df.empty:
        raise ValueError("Leerer DataFrame: Fibonacci-Level koennen nicht berechnet werden.")

    high = float(np.max(df["High"]))
    low = float(np.min(df["Low"]))
    high_date = df["High"].idxmax()
    low_date = df["Low"].idxmin()

    price_range = high - low
    levels = {
        ratio: high - price_range * ratio for ratio in FIBONACCI_RATIOS
    }

    return FibonacciResult(
        high=high,
        low=low,
        high_date=high_date,
        low_date=low_date,
        levels=levels,
    )
