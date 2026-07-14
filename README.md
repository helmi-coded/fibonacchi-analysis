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
├── .streamlit/config.toml  # Theme-Einstellungen
└── .gitignore
```

Die drei Schichten (Daten, Berechnung, UI) sind bewusst getrennt: `fibonacci.py`
hängt weder von Streamlit noch von yfinance ab und lässt sich isoliert testen.

## Funktionsumfang

- Ticker-Eingabe (z. B. `AAPL`, `MSFT`, `SAP.DE`)
- Zeitraum-Auswahl: 1 Monat, 200 Tage, 1 Jahr, 5 Jahre
- Berechnung von Hoch/Tief im gewählten Zeitraum
- Klassische Fibonacci-Retracement-Level: 0 %, 23,6 %, 38,2 %, 50 %, 61,8 %, 100 %
- Interaktiver Candlestick-Chart (Plotly) mit eingezeichneten Fibonacci-Linien
- Kennzahlen-Kopfzeile (letzter Kurs, Hoch, Tief, Spanne)

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
- Ergebnisse werden pro Ticker/Zeitraum 15 Minuten gecacht (`st.cache_data`),
  um unnötige API-Aufrufe zu vermeiden.
- Die App dient ausschließlich Informationszwecken und stellt keine
  Anlageberatung dar.
