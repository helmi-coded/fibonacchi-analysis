# Fibonacci-Retracement-Analyse

Interaktive Streamlit-App zur Visualisierung von Fibonacci-Retracement-Leveln
für beliebige Aktien-Ticker, auf Basis von Live-Kursdaten (Yahoo Finance).

## Projektstruktur

```
fibonacci-app/
├── app.py              # Streamlit-UI (Sidebar, Chart, Kennzahlen)
├── data_fetcher.py      # Datenbeschaffung via yfinance (mit Caching)
├── fibonacci.py         # Berechnungslogik (Hoch/Tief, Retracement-Level)
├── requirements.txt      # Python-Abhängigkeiten
├── runtime.txt           # pinnt Python 3.11 für Streamlit Cloud (Stabilität)
├── .streamlit/config.toml  # Theme-Einstellungen
└── .gitignore
```

Die drei Schichten (Daten, Berechnung, UI) sind bewusst getrennt: `fibonacci.py`
hängt weder von Streamlit noch von yfinance ab und lässt sich isoliert testen.

## Funktionsumfang

Geführter 5-Schritte-Ablauf nach der klassischen manuellen
Fibonacci-Retracement-Methode (statt einer automatischen Ganzzeitraum-Analyse):

1. **Ticker & Zeitraum wählen** (Sidebar) - z. B. `AAPL`, `MSFT`, `SAP.DE`; Zeitraum: 1 Monat, 200 Handelstage (GD 200), 1 Jahr, 5 Jahre.
2. **Kurschart ansehen** - Candlestick-Chart (Plotly) zur optischen Trendbeurteilung.
3. **Trendrichtung bestimmen** - Auf- oder Abwärtstrend, mit automatischem Vorschlag.
4. **Extrempunkte identifizieren** - Zeitfenster-Regler für die relevante Trendbewegung; die App ermittelt darin präzise Hoch (H) und Tief (T) samt Datum, inkl. Plausibilitätsprüfung gegen die gewählte Trendrichtung.
5. **Differenz & Fibonacci-Level** - Spanne (D = H − T) und die klassischen Level (0 %, 23,6 %, 38,2 %, 50 %, 61,8 %, 78,6 %, 100 %) werden automatisch berechnet und im Chart sowie als Tabelle dargestellt. Die Formel ist trendrichtungsabhängig (Aufwärtstrend: `H − D×Ratio`; Abwärtstrend: `T + D×Ratio`).

Alle Kurse werden in der Original-Handelswährung des Tickers angezeigt (keine Euro-Umrechnung).

## Lokal starten

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Die App ist danach unter `http://localhost:8501` erreichbar.

## Deployment auf Streamlit Community Cloud

1. **GitHub-Repository anlegen** und den Inhalt dieses Ordners hochladen:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Fibonacci-Retracement-App"
   git branch -M main
   git remote add origin https://github.com/<dein-user>/<dein-repo>.git
   git push -u origin main
   ```
2. Auf [streamlit.io/cloud](https://streamlit.io/cloud) einloggen (GitHub-Login).
3. **"New app"** → Repository, Branch (`main`) und `app.py` als Hauptdatei auswählen.
4. **Deploy** klicken. Streamlit Cloud installiert `requirements.txt` automatisch.
5. Die App ist danach über eine öffentliche `*.streamlit.app`-URL erreichbar.

Da die App ausschließlich mit Live-API-Abfragen arbeitet (keine lokale
Datenbank, keine gespeicherten Zugangsdaten), sind keine Secrets oder
zusätzliche Konfiguration nötig.

## Hinweise

- Datenquelle ist Yahoo Finance über die `yfinance`-Bibliothek; Kurse werden
  in der jeweiligen Handelswährung des Tickers angezeigt.
- Ergebnisse werden pro Ticker/Zeitraum gecacht (`st.cache_data`: Kurse 30
  Minuten, Name/Währung 60 Minuten), um unnötige API-Aufrufe zu vermeiden.
  Bei einem Yahoo-Finance-Rate-Limit ("Too Many Requests") versucht die App
  automatisch mit kurzer Wartezeit erneut.
- Die App dient ausschließlich Informationszwecken und stellt keine
  Anlageberatung dar.
