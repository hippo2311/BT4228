# Regime-Adaptive Quantitative Trading System

A full-stack quantitative trading dashboard for the top 10 large-cap U.S. stocks.

**Backend** — Python Flask API running a MACD + Bollinger Bands + ATR strategy, Modern Portfolio Theory optimisation, and GPT-powered AI explanations.
**Frontend** — React 19 + Vite dashboard with four pages: Dashboard, Portfolio, Monitoring, and AI Insights.

---

## Quick Start

### Prerequisites

| Requirement | Version |
| ----------- | ------- |
| Python      | 3.11+   |
| Node.js     | 18+     |
| npm         | 9+      |

---

### 1. Clone & install dependencies

```bash
# Frontend dependencies
npm install

# Python virtual environment (already created)
# Activate and install backend dependencies
source .venv/bin/activate
python -m pip install flask flask-cors scipy scikit-learn ta openai python-dotenv yfinance numpy pandas
```

---

### 2. Set up environment variables

Create a `.env` file in the project root:

```
OPENAI_API='your-openai-api-key-here'
```

> The AI features (trade explanations, market summary, chat) use **GPT-4o-mini** via the OpenAI API.
> All other features (strategy, portfolio optimisation, metrics) work without an API key.

---

### 3. Run the backend

```bash
# From the project root
PORT=5001 .venv/bin/python backend/app.py
```

On first start the backend will:

1. Download ~5 years of daily price data for all 10 tickers from Yahoo Finance (~15–30 s)
2. Compute MACD, Bollinger Bands, and ATR indicators
3. Run the bar-by-bar strategy simulation
4. Optimise portfolio weights using Modern Portfolio Theory
5. Compute all performance metrics

Once you see `=== Data ready ===` in the terminal, the API is serving on `http://localhost:5001`.

**Check status:**

```bash
curl http://localhost:5001/api/status
# → {"status":"ready", ...}
```

---

### 4. Run the frontend

Open a **second terminal**:

```bash
npm run dev
```

Frontend starts at `http://localhost:5173`. Vite automatically proxies all `/api/*` calls to the Flask backend.

---

## Interactive Brokers Paper Trading

The current project is a research/dashboard app by default. It does **not** place broker orders unless you run the dedicated IBKR bridge script.

Add these variables to `.env`:

```bash
OPENAI_API='your-openai-api-key-here'
IBKR_HOST='127.0.0.1'
IBKR_PORT='7497'
IBKR_CLIENT_ID='1'
```

Install the IBKR bridge dependency:

```bash
source .venv/bin/activate
python -m pip install ib_insync
```

Before running the bridge:

1. Start `TWS` or `IB Gateway`
2. Log in with `Paper Trading`
3. Enable API access
4. Use paper port `7497` for TWS, or adjust `IBKR_PORT` if you use IB Gateway

Preview the orders first:

```bash
.venv/bin/python backend/ibkr_paper.py
```

Submit to IBKR paper trading:

```bash
.venv/bin/python backend/ibkr_paper.py --execute --close-extra --allow-short
```

What the bridge does:

1. Runs the existing walk-forward strategy locally.
2. Reads `final_positions` and optimizer weights from the strategy output.
3. Scales target share counts to your current IBKR paper account equity.
4. Compares those targets against your existing IBKR positions.
5. Prints the order plan, or submits market orders when `--execute` is present.

Notes:

- Default mode is dry-run only.
- `--close-extra` closes IBKR positions that are not part of the strategy target.
- `--allow-short` is required if you want the bridge to send short orders.
- IBKR requires `TWS` or `IB Gateway` to stay running while the script connects and places orders.
- IBKR paper data may be delayed unless your account has the required market data entitlements.

---

### 5. Open the dashboard

Navigate to **http://localhost:5173** in your browser.

> If the backend is still loading data, the frontend will display synthetic placeholder data and switch to live data automatically once the backend is ready.

---

## Project Structure

```
.
├── backend/
│   ├── app.py            # Flask API server (all routes)
│   ├── trading.py        # MACD-BB-ATR strategy + simulation engine
│   ├── optimizer.py      # MPT portfolio optimiser (Ledoit-Wolf + tangent portfolio)
│   ├── performance.py    # Performance metrics (Sharpe, drawdown, CAGR, etc.)
│   └── ai_service.py     # GPT-powered trade explanations, summary, chat
│
├── src/
│   ├── services/
│   │   └── api.js        # Frontend API client (fetches from /api/*)
│   ├── pages/
│   │   ├── Dashboard.jsx   # Overview: KPIs, equity curve, signals, alerts
│   │   ├── Portfolio.jsx   # Allocation, efficient frontier, risk contribution
│   │   ├── Monitoring.jsx  # Live positions, signal feed, drawdown, exposure
│   │   └── AIInsights.jsx  # Trade explainer, market summary, risk alerts, chat
│   ├── components/
│   │   ├── Layout.jsx      # Sidebar + top bar shell
│   │   ├── KPICard.jsx     # Metric card with sparkline
│   │   └── SignalBadge.jsx # LONG / SHORT / EXIT badge
│   └── data/
│       └── synthetic.js    # Fallback placeholder data (used when backend is offline)
│
├── notebook/
│   └── Group6_FinalTerm.ipynb  # Original research notebook (strategy source)
│
├── .env                  # OPENAI_API key (not committed)
├── vite.config.js        # Vite config with /api proxy → localhost:5001
└── package.json
```

---

## API Endpoints

| Method | Path              | Description                                                |
| ------ | ----------------- | ---------------------------------------------------------- |
| GET    | `/api/status`     | Backend load state: `loading` / `ready` / `error`          |
| GET    | `/api/dashboard`  | All data for the Dashboard page                            |
| GET    | `/api/portfolio`  | Portfolio allocation, efficient frontier, sector breakdown |
| GET    | `/api/monitoring` | Positions, signals, KPIs, drawdown, sector exposure        |
| GET    | `/api/alerts`     | AI-generated risk alerts                                   |
| POST   | `/api/ai/explain` | Explain a trading signal (GPT)                             |
| POST   | `/api/ai/summary` | Generate market summary (GPT)                              |
| POST   | `/api/ai/chat`    | Chat with AI assistant (GPT)                               |
| POST   | `/api/refresh`    | Re-run the backtest and reload all data                    |

---

## Trading Strategy

The strategy is extracted from `notebook/Group6_FinalTerm.ipynb` and implements four entry mechanisms:

| Code   | Name            | Entry Condition                                 |
| ------ | --------------- | ----------------------------------------------- |
| **LM** | Long Momentum   | `0 ≤ MACD_hist ≤ Z_mid` AND `price > BB_mid`    |
| **SM** | Short Momentum  | `−Z_mid ≤ MACD_hist < 0` AND `price < BB_mid`   |
| **LR** | Long Reversion  | `MACD_hist < −Z_extreme` AND `price < BB_lower` |
| **SR** | Short Reversion | `MACD_hist > Z_extreme` AND `price > BB_upper`  |

Exits are ATR-scaled stop-loss / take-profit with optional trailing stops and a time-based exit.
`Z_extreme` and `Z_mid` are dynamically scaled using **Robust MAD** of the MACD histogram.

**Universe:** AAPL, AMZN, META, GOOG, GOOGL, NVDA, MSFT, AVGO, TSLA, BRK-B
**Benchmark:** SPY (buy-and-hold)

---

## Portfolio Optimisation

Uses **Modern Portfolio Theory** (Ledoit-Wolf shrinkage covariance + analytical tangent portfolio) to find the max-Sharpe allocation. The efficient frontier is computed with `scipy` SLSQP.

---

## Tech Stack

| Layer                  | Technology                         |
| ---------------------- | ---------------------------------- |
| Frontend framework     | React 19 + Vite 8                  |
| Styling                | Tailwind CSS v4                    |
| Charts                 | Recharts v3                        |
| Icons                  | Lucide React                       |
| Routing                | React Router v7                    |
| Backend framework      | Flask 3 + flask-cors               |
| Market data            | yfinance                           |
| Technical indicators   | ta (TA-Lib wrapper)                |
| Portfolio optimisation | scipy + scikit-learn (Ledoit-Wolf) |
| AI features            | OpenAI GPT-4o-mini                 |

---

## Troubleshooting

**Port 5000 already in use (macOS)**
macOS AirPlay Receiver uses port 5000. Use `PORT=5001` as shown above, or disable AirPlay Receiver in System Settings → General → AirDrop & Handoff.

**Backend stuck on "loading"**
Check logs in the backend terminal. Yahoo Finance rate-limits may slow data downloads. Wait 30–60 seconds.

**AI features return template responses**
Ensure `.env` contains a valid `OPENAI_API` key. The key is loaded automatically at backend startup.

**Frontend shows synthetic data**
The frontend falls back to `src/data/synthetic.js` if the backend is unreachable. Start the Flask server first, then hard-refresh the browser.
