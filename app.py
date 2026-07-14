"""
app.py
------
Streamlit-Einstiegspunkt (UI-Schicht). Enthaelt bewusst keine Berechnungs-
oder Datenbeschaffungslogik - diese liegt in fibonacci.py bzw. data_fetcher.py.

Gefuehrter 5-Schritte-Ablauf (folgt der klassischen manuellen
Fibonacci-Retracement-Methode statt einer automatischen Ganzzeitraum-Analyse):

    Schritt 1: Ticker & Zeitraum waehlen (Sidebar)
    Schritt 2: Kurschart erscheint - Trend optisch beurteilen
    Schritt 3: Trendrichtung bestimmen (Auf-/Abwaertstrend)
    Schritt 4: Extrempunkte identifizieren (Zeitfenster fuer die Trendbewegung)
    Schritt 5: Differenz & Fibonacci-Level werden berechnet und dargestellt

Start lokal:    streamlit run app.py
Deployment:     siehe README.md (Streamlit Community Cloud)
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_fetcher import PERIOD_CONFIG, DataFetchError, fetch_price_history, fetch_ticker_meta
from fibonacci import FIBONACCI_RATIOS, TREND_DOWN, TREND_UP, calculate_fibonacci_levels

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
    0.786: "#9b59b6",
    1.0: "#7f8c8d",
}

TREND_OPTIONS = {
    "Aufwärtstrend (Tief → Hoch)": TREND_UP,
    "Abwärtstrend (Hoch → Tief)": TREND_DOWN,
}


# ---------------------------------------------------------------------------
# Sidebar: Schritt 1 - Ticker & Zeitraum
# ---------------------------------------------------------------------------
def render_sidebar() -> tuple[str, str]:
    st.sidebar.header("Schritt 1: Ticker & Zeitraum")
    ticker = st.sidebar.text_input(
        "Ticker-Symbol",
        value="AAPL",
        help="Beispiele: AAPL, MSFT, SAP.DE, ^GSPC",
    ).strip()

    period_label = st.sidebar.selectbox(
        "Zeitraum",
        options=list(PERIOD_CONFIG.keys()),
        index=2,  # Standard: "1 Jahr"
        help="Definiert nur, wie viel Kurshistorie geladen wird - die eigentliche "
        "Trendbewegung für die Fibonacci-Berechnung wählst du in Schritt 4 selbst.",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Datenquelle: Yahoo Finance (yfinance), Kurse in der jeweiligen "
        "Handelswaehrung des Tickers."
    )
    return ticker, period_label


# ---------------------------------------------------------------------------
# Chart-Bausteine
# ---------------------------------------------------------------------------
def _add_candlestick_trace(fig: go.Figure, df, ticker: str, currency: str) -> None:
    """Fuegt den Kursverlauf als Candlestick hinzu (bevorzugter Chart-Typ)."""
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


def _add_line_fallback_trace(fig: go.Figure, df, ticker: str, currency: str) -> None:
    """
    Fallback-Chart als einfache Linie (Schlusskurs), falls der Candlestick-Trace
    in der Zielumgebung aus irgendeinem Grund fehlschlaegt (z. B. abweichende
    Plotly-/Python-Version auf dem Deployment-Host). Bewusst ohne exotische
    Properties gehalten, um maximale Kompatibilitaet sicherzustellen.
    """
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name=ticker.upper(),
            line=dict(color="#2c3e50", width=1.6),
            hovertemplate=f"Datum: %{{x|%d.%m.%y}}<br>Schlusskurs: %{{y:,.2f}} {currency}<extra></extra>",
        )
    )


def _base_layout(fig: go.Figure, title: str, currency: str) -> None:
    fig.update_layout(
        title=title,
        xaxis_title="Datum",
        yaxis_title=f"Kurs ({currency})",
        yaxis_ticksuffix=f" {currency}",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=550,
        margin=dict(l=40, r=120, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def build_base_chart(df, ticker: str, company_name: str, currency: str) -> go.Figure:
    """Schritt-2-Chart: reiner Kursverlauf ohne Fibonacci-Level, zur optischen Trendbeurteilung."""
    fig = go.Figure()
    try:
        _add_candlestick_trace(fig, df, ticker, currency)
    except Exception:
        fig = go.Figure()
        _add_line_fallback_trace(fig, df, ticker, currency)
        st.warning(
            "Der Candlestick-Chart konnte in dieser Umgebung nicht dargestellt "
            "werden - es wird stattdessen eine Linienansicht des Schlusskurses "
            "angezeigt."
        )
    _base_layout(fig, f"{company_name} ({ticker.upper()}) - Kursverlauf", currency)
    return fig


def build_fibonacci_chart(
    df, fib_result, ticker: str, company_name: str, currency: str, swing_start, swing_end
) -> go.Figure:
    """Schritt-5-Chart: Kursverlauf + markiertes Zeitfenster der Trendbewegung + Fibonacci-Level."""
    fig = go.Figure()
    try:
        _add_candlestick_trace(fig, df, ticker, currency)
    except Exception:
        fig = go.Figure()
        _add_line_fallback_trace(fig, df, ticker, currency)
        st.warning(
            "Der Candlestick-Chart konnte in dieser Umgebung nicht dargestellt "
            "werden - es wird stattdessen eine Linienansicht des Schlusskurses "
            "angezeigt."
        )

    # Das vom Nutzer gewaehlte Zeitfenster der Trendbewegung (Schritt 4) im
    # Chart hervorheben.
    fig.add_vrect(
        x0=swing_start,
        x1=swing_end,
        fillcolor="#3498db",
        opacity=0.08,
        line_width=0,
        annotation_text="gewählte Trendbewegung",
        annotation_position="top left",
        annotation_font_size=10,
    )

    # Erkannte Extrempunkte (H und T) direkt im Chart markieren.
    fig.add_trace(
        go.Scatter(
            x=[fib_result.high_date, fib_result.low_date],
            y=[fib_result.high, fib_result.low],
            mode="markers+text",
            text=["H", "T"],
            textposition="top center",
            marker=dict(size=11, color="#2c3e50", symbol="diamond"),
            name="Erkannte Extrempunkte",
            hovertemplate="%{text}: %{y:,.2f} " + currency + "<extra></extra>",
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
            annotation_text=f"{ratio * 100:.1f}%{fib_result.anchor_label(ratio)}  ({price:,.2f} {currency})",
            annotation_position="right",
            annotation_font_size=11,
            annotation_font_color=LEVEL_COLORS[ratio],
        )

    _base_layout(
        fig,
        f"{company_name} ({ticker.upper()}) - Fibonacci-Retracement ({fib_result.trend_label})",
        currency,
    )
    return fig


# ---------------------------------------------------------------------------
# Hauptlogik
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("📈 Fibonacci-Retracement-Analyse")
    st.caption(
        "Geführter Ablauf nach der klassischen Fibonacci-Retracement-Methode: "
        "Trend beurteilen, Extrempunkte auswählen, Level berechnen."
    )

    ticker, period_label = render_sidebar()

    if not ticker:
        st.info("Bitte links ein Ticker-Symbol eingeben.")
        return

    try:
        with st.spinner(f"Lade Kursdaten fuer {ticker.upper()}..."):
            df = fetch_price_history(ticker, period_label)
            meta = fetch_ticker_meta(ticker)
    except DataFetchError as exc:
        st.error(str(exc))
        return

    company_name = meta["name"]
    currency = meta["currency"]  # Original-Handelswaehrung des Tickers, keine Umrechnung.

    # Hinweis, falls im "Handelstage"-Modus weniger Datenpunkte vorliegen als
    # angefordert (z. B. bei sehr jungen Boersengaengen).
    period_config = PERIOD_CONFIG[period_label]
    if period_config["mode"] == "trading" and len(df) < period_config["count"]:
        st.info(
            f"Hinweis: Für {ticker.upper()} liegen nur {len(df)} von "
            f"{period_config['count']} angeforderten Handelstagen vor "
            "(vermutlich kürzere Börsenhistorie)."
        )

    if len(df) < 2:
        st.error("Zu wenige Kursdatenpunkte für diesen Zeitraum. Bitte anderen Zeitraum wählen.")
        return

    # ------------------------------------------------------------------ #
    # Schritt 2: Kurschart
    # ------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("Schritt 2: Kursverlauf")
    st.caption(
        "Sieh dir den Kursverlauf an und verschaffe dir einen Eindruck von der "
        "aktuellen Trendrichtung - das brauchst du für Schritt 3."
    )
    st.plotly_chart(build_base_chart(df, ticker, company_name, currency), use_container_width=True)

    # ------------------------------------------------------------------ #
    # Schritt 3: Trendrichtung bestimmen
    # ------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("Schritt 3: Trendrichtung bestimmen")
    st.caption(
        "Aufwärtstrend: Sie identifizieren den absoluten Tiefpunkt (T) und den "
        "jüngsten Höchstpunkt (H) der Bewegung. Abwärtstrend: Sie identifizieren "
        "den absoluten Höchstpunkt (H) und den jüngsten Tiefpunkt (T) der Bewegung."
    )

    # Automatischer Vorschlag als Startpunkt (Vergleich erster vs. letzter
    # Schlusskurs im geladenen Zeitraum) - der Nutzer entscheidet trotzdem selbst.
    suggested_trend = TREND_UP if df["Close"].iloc[-1] >= df["Close"].iloc[0] else TREND_DOWN
    trend_labels = list(TREND_OPTIONS.keys())
    default_index = next(i for i, label in enumerate(trend_labels) if TREND_OPTIONS[label] == suggested_trend)

    trend_label = st.radio(
        "Trendrichtung im gewählten Zeitraum",
        options=trend_labels,
        index=default_index,
        horizontal=True,
        help="Vorbelegt anhand von erstem vs. letztem Schlusskurs im Zeitraum - bitte selbst prüfen und ggf. ändern.",
    )
    trend = TREND_OPTIONS[trend_label]

    # ------------------------------------------------------------------ #
    # Schritt 4: Extrempunkte identifizieren
    # ------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("Schritt 4: Extrempunkte identifizieren")
    st.caption(
        "Ziehe den Regler auf das Zeitfenster der relevanten Trendbewegung aus "
        "Schritt 2/3. Die App ermittelt darin automatisch das exakte Hoch und "
        "Tief samt Datum."
    )

    trading_dates = list(df.index)
    swing_start, swing_end = st.select_slider(
        "Zeitfenster der Trendbewegung",
        options=trading_dates,
        value=(trading_dates[0], trading_dates[-1]),
        format_func=lambda d: d.strftime("%d.%m.%y"),
    )
    if swing_start > swing_end:
        swing_start, swing_end = swing_end, swing_start

    swing_df = df.loc[swing_start:swing_end]
    if len(swing_df) < 2:
        st.warning("Bitte ein Zeitfenster mit mindestens zwei Handelstagen wählen.")
        return

    try:
        fib_result = calculate_fibonacci_levels(swing_df, trend=trend)
    except ValueError as exc:
        st.error(f"Berechnungsfehler: {exc}")
        return

    # Plausibilitätsprüfung: passt die chronologische Reihenfolge von H/T zur
    # gewählten Trendrichtung?
    if trend == TREND_UP and fib_result.low_date > fib_result.high_date:
        st.warning(
            "Hinweis: Im gewählten Zeitfenster liegt das Tief zeitlich NACH dem "
            "Hoch - das passt nicht zur Definition 'Aufwärtstrend' (erst Tief, "
            "dann jüngeres Hoch). Zeitfenster anpassen oder Trendrichtung auf "
            "'Abwärtstrend' wechseln."
        )
    elif trend == TREND_DOWN and fib_result.high_date > fib_result.low_date:
        st.warning(
            "Hinweis: Im gewählten Zeitfenster liegt das Hoch zeitlich NACH dem "
            "Tief - das passt nicht zur Definition 'Abwärtstrend' (erst Hoch, "
            "dann jüngeres Tief). Zeitfenster anpassen oder Trendrichtung auf "
            "'Aufwärtstrend' wechseln."
        )

    col_h, col_t = st.columns(2)
    col_h.metric("Erkanntes Hoch (H)", f"{fib_result.high:,.2f} {currency}", help=str(fib_result.high_date.date()))
    col_t.metric("Erkanntes Tief (T)", f"{fib_result.low:,.2f} {currency}", help=str(fib_result.low_date.date()))

    # ------------------------------------------------------------------ #
    # Schritt 5: Differenz & Fibonacci-Level
    # ------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("Schritt 5: Fibonacci-Level")

    col1, col2, col3 = st.columns(3)
    last_close = float(df["Close"].iloc[-1])
    col1.metric("Letzter Schlusskurs", f"{last_close:,.2f} {currency}")
    col2.metric("Spanne (D = H − T)", f"{fib_result.range:,.2f} {currency}")
    col3.metric("Trendrichtung", fib_result.trend_label)

    try:
        fig = build_fibonacci_chart(df, fib_result, ticker, company_name, currency, swing_start, swing_end)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.error("Der Chart konnte nicht erstellt werden.")
        with st.expander("Technische Details anzeigen"):
            st.exception(exc)

    with st.expander("Fibonacci-Level als Tabelle anzeigen", expanded=True):
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
    Definition der Zeitraeume (Schritt 1) sowie die Berechnungslogik der
    Fibonacci-Level (Schritt 3-5).
    """
    st.markdown("---")
    st.subheader("Erklärung: Ablauf, Zeiträume & Berechnungslogik")

    st.markdown(
        """
**Der 5-Schritte-Ablauf dieser App:**

1. **Ticker & Zeitraum wählen** (Sidebar) - legt fest, wie viel Kurshistorie geladen wird.
2. **Kurschart ansehen** - Grundlage für die eigene Einschätzung der Trendrichtung.
3. **Trendrichtung bestimmen** - Sie entscheiden: Auf- oder Abwärtstrend.
4. **Extrempunkte identifizieren** - Sie wählen das Zeitfenster der relevanten Bewegung; die App ermittelt darin präzise Hoch (H) und Tief (T).
5. **Differenz & Level** - die App berechnet Spanne und Fibonacci-Level automatisch.

**Zeiträume in Schritt 1 (nur Datengrundlage, nicht die eigentliche Trendbewegung):**

| Zeitraum | Basis | Was genau wird geladen? |
|---|---|---|
| 1 Monat | Kalendertage | heute − 30 Kalendertage bis heute |
| 200 Handelstage (GD 200) | Handelstage | die letzten 200 tatsächlichen Börsenhandelstage |
| 1 Jahr | Kalendertage | heute − 365 Kalendertage bis heute |
| 5 Jahre | Kalendertage | heute − 1.825 Kalendertage (365 × 5) bis heute |

Bei "1 Monat", "1 Jahr" und "5 Jahre" wird auf Kalendertage zurückgegriffen; der
Datensatz enthält entsprechend weniger Kursdatenpunkte als Kalendertage, da an
Wochenenden/Feiertagen nicht gehandelt wird. "200 Handelstage (GD 200)" lädt
stattdessen gezielt die letzten 200 tatsächlichen Handelstage.

**Berechnungslogik der Fibonacci-Level (Schritt 5):**

Innerhalb des in Schritt 4 gewählten Zeitfensters:

1. Hoch (H) = höchster Tages-Höchstkurs (`High`)
2. Tief (T) = niedrigster Tages-Tiefstkurs (`Low`)
3. Spanne: `D = H − T`
4. Für jedes Retracement-Verhältnis (0 %, 23,6 %, 38,2 %, 50 %, 61,8 %, 78,6 %, 100 %), abhängig von der in Schritt 3 gewählten Trendrichtung:

   - **Aufwärtstrend** (T → H): `Level = H − D × Ratio` → 0 % = Hoch, 100 % = Tief
   - **Abwärtstrend** (H → T): `Level = T + D × Ratio` → 0 % = Tief, 100 % = Hoch

Die Trendrichtung bestimmt also nicht nur die Beschriftung, sondern auch die
konkreten Kurswerte der einzelnen Level (mit Ausnahme von 50 % sowie dem
komplementären Paar 38,2 %/61,8 %, die bei beiden Richtungen identisch sind).
Deshalb ist die in Schritt 3 gewählte Richtung wichtig für ein korrektes
Ergebnis.
"""
    )


if __name__ == "__main__":
    main()
