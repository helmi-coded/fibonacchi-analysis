"""
app.py
------
Streamlit-Einstiegspunkt (UI-Schicht). Enthaelt bewusst keine Berechnungs-
oder Datenbeschaffungslogik - diese liegt in fibonacci.py bzw. data_fetcher.py.

Start lokal:    streamlit run app.py
Deployment:     siehe README.md (Streamlit Community Cloud)
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_fetcher import PERIOD_TO_DAYS, DataFetchError, fetch_price_history, fetch_ticker_meta
from fibonacci import FIBONACCI_RATIOS, calculate_fibonacci_levels

# ---------------------------------------------------------------------------
# Seitenkonfiguration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Fibonacci-Retracement-Analyse",
    page_icon="📈",
    layout="wide",
)

# Farbschema fuer die einzelnen Fibonacci-Level (0 % und 100 % = Extrempunkte).
LEVEL_COLORS = {
    0.0: "#7f8c8d",
    0.236: "#e67e22",
    0.382: "#f1c40f",
    0.5: "#2ecc71",
    0.618: "#3498db",
    1.0: "#7f8c8d",
}


# ---------------------------------------------------------------------------
# Sidebar: Nutzereingaben
# ---------------------------------------------------------------------------
def render_sidebar() -> tuple[str, str]:
    st.sidebar.header("Einstellungen")
    ticker = st.sidebar.text_input(
        "Ticker-Symbol",
        value="AAPL",
        help="Beispiele: AAPL, MSFT, SAP.DE, ^GSPC",
    ).strip()

    period_label = st.sidebar.selectbox(
        "Zeitraum",
        options=list(PERIOD_TO_DAYS.keys()),
        index=2,  # Standard: "1 Jahr"
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Datenquelle: Yahoo Finance (yfinance), Kurse in der jeweiligen "
        "Handelswaehrung des Tickers."
    )
    return ticker, period_label


# ---------------------------------------------------------------------------
# Chart-Aufbau
# ---------------------------------------------------------------------------
def build_chart(df, fib_result, ticker: str, company_name: str, currency: str) -> go.Figure:
    fig = go.Figure()

    # Kursverlauf als Candlestick fuer maximale Informationsdichte.
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker.upper(),
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c",
            # Waehrung explizit im Hover-Tooltip ausweisen.
            hovertemplate=(
                "Datum: %{x|%d.%m.%y}<br>"
                f"Open: %{{open:,.2f}} {currency}<br>"
                f"High: %{{high:,.2f}} {currency}<br>"
                f"Low: %{{low:,.2f}} {currency}<br>"
                f"Close: %{{close:,.2f}} {currency}"
                "<extra></extra>"
            ),
        )
    )

    # Fibonacci-Level als horizontale Linien ueber den gesamten Chartbereich.
    for ratio in FIBONACCI_RATIOS:
        price = fib_result.levels[ratio]
        fig.add_hline(
            y=price,
            line_dash="dash",
            line_color=LEVEL_COLORS[ratio],
            line_width=1.3,
            annotation_text=f"{ratio * 100:.1f}%  ({price:,.2f} {currency})",
            annotation_position="right",
            annotation_font_size=11,
            annotation_font_color=LEVEL_COLORS[ratio],
        )

    fig.update_layout(
        title=f"{company_name} ({ticker.upper()}) - Kursverlauf mit Fibonacci-Retracement",
        xaxis_title="Datum",
        yaxis_title=f"Kurs ({currency})",
        yaxis_ticksuffix=f" {currency}",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=650,
        margin=dict(l=40, r=120, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ---------------------------------------------------------------------------
# Hauptlogik
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("📈 Fibonacci-Retracement-Analyse")
    st.caption(
        "Interaktive Visualisierung von Fibonacci-Retracement-Leveln zur "
        "Identifikation potenzieller Einstiegspunkte."
    )

    ticker, period_label = render_sidebar()

    if not ticker:
        st.info("Bitte links ein Ticker-Symbol eingeben.")
        return

    try:
        with st.spinner(f"Lade Kursdaten fuer {ticker.upper()}..."):
            df = fetch_price_history(ticker, period_label)
            meta = fetch_ticker_meta(ticker)
        fib_result = calculate_fibonacci_levels(df)
    except DataFetchError as exc:
        st.error(str(exc))
        return
    except ValueError as exc:
        st.error(f"Berechnungsfehler: {exc}")
        return

    company_name = meta["name"]
    currency = meta["currency"]  # Original-Handelswaehrung des Tickers, keine Umrechnung.

    # Kennzahlen-Kopfzeile
    col1, col2, col3, col4 = st.columns(4)
    last_close = float(df["Close"].iloc[-1])
    col1.metric("Letzter Schlusskurs", f"{last_close:,.2f} {currency}")
    col2.metric(
        "Hoch (Zeitraum)", f"{fib_result.high:,.2f} {currency}", help=str(fib_result.high_date.date())
    )
    col3.metric(
        "Tief (Zeitraum)", f"{fib_result.low:,.2f} {currency}", help=str(fib_result.low_date.date())
    )
    col4.metric("Spanne", f"{fib_result.range:,.2f} {currency}")

    # Chart
    fig = build_chart(df, fib_result, ticker, company_name, currency)
    st.plotly_chart(fig, use_container_width=True)

    # Level-Tabelle
    with st.expander("Fibonacci-Level als Tabelle anzeigen"):
        st.dataframe(
            fib_result.as_dataframe(currency=currency),
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Hinweis: Diese App dient ausschliesslich Informationszwecken und "
        "stellt keine Anlageberatung dar. Alle Kurse werden in der "
        "Original-Handelswaehrung des jeweiligen Tickers angezeigt (keine "
        "Umrechnung in Euro)."
    )

    render_interval_explanation()


def render_interval_explanation() -> None:
    """
    Permanenter, immer sichtbarer Erklaerungsblock am Seitenende:
    Definition der wählbaren Zeitraeume sowie die Berechnungslogik der
    Fibonacci-Level je Zeitraum.
    """
    st.markdown("---")
    st.subheader("Erklärung: Zeiträume & Berechnungslogik")

    st.markdown(
        """
**Definition der Zeiträume** (jeweils Kalendertage, nicht Handelstage,
gerechnet vom heutigen Datum rückwärts):

| Zeitraum | Kalendertage | Zeitfenster |
|---|---|---|
| 1 Monat | 30 Tage | heute − 30 Tage bis heute |
| 200 Tage | 200 Tage | heute − 200 Tage bis heute |
| 1 Jahr | 365 Tage | heute − 365 Tage bis heute |
| 5 Jahre | 1.825 Tage (365 × 5) | heute − 1.825 Tage bis heute |

Da an Wochenenden und Feiertagen nicht gehandelt wird, enthält der
Datensatz entsprechend weniger Kursdatenpunkte als Kalendertage.

**Berechnungslogik der Fibonacci-Level** (identisch für jeden Zeitraum,
nur Hoch/Tief unterscheiden sich):

1. Hoch = höchster Tages-Höchstkurs (`High`) innerhalb des gewählten Zeitraums
2. Tief = niedrigster Tages-Tiefstkurs (`Low`) innerhalb des gewählten Zeitraums
3. Für jedes Retracement-Verhältnis (0 %, 23,6 %, 38,2 %, 50 %, 61,8 %, 100 %):

   `Level = Hoch − (Hoch − Tief) × Ratio`

   → 0 % entspricht dem Hoch, 100 % entspricht dem Tief.

Ein längerer Zeitraum (z. B. 5 Jahre) führt in der Regel zu einer größeren
Hoch-Tief-Spanne und damit zu weiter auseinanderliegenden Fibonacci-Leveln
als ein kurzer Zeitraum (z. B. 1 Monat) - die Formel selbst bleibt dabei
unverändert.
"""
    )


if __name__ == "__main__":
    main()
