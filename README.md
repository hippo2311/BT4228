# Regime-Adaptive Quantitative Trading System - Frontend Dashboard

A React-based frontend dashboard for a regime-adaptive quantitative trading platform targeting the top 10 large-cap U.S. stocks.

This is a **UI blueprint / design prototype** with placeholder data. All data is synthetic and defined in `src/data/synthetic.js`. The codebase is fully annotated with comments explaining what each section displays, which system component it belongs to, and what real data source should replace the placeholders.

## System Components

The trading system has **4 core components**, each mapped to specific pages and sections in the dashboard:

| Component | Description | Primary Page | Also Appears On |
|-----------|-------------|-------------|-----------------|
| **Algorithmic Trading Strategies** | Generates buy/sell signals using MACD, Bollinger Bands, and ATR. Implements 4 mechanisms: Long Momentum (LM), Short Momentum (SM), Long Reversion (LR), Short Reversion (SR). | `/monitoring` | `/` (signals table) |
| **Portfolio Optimization** | Allocates capital across stocks using Modern Portfolio Theory to maximize Sharpe ratio. Outputs target weights, efficient frontier, risk contributions. | `/portfolio` | `/` (KPIs, donut chart) |
| **Real-Time Monitoring** | Tracks live portfolio performance: P&L, equity curve, volatility, drawdowns, sector exposure. | `/monitoring` | `/` (equity curve, KPIs) |
| **AI-Assisted Explanations** | Uses LLM (Claude API) to explain trades, summarize markets, generate risk alerts, and answer questions via chat. | `/ai-insights` | `/` (alerts feed) |

### Important Distinction

- **Algorithmic Trading** decides *when* to buy/sell (signal generation)
- **Portfolio Optimization** decides *how much* to allocate (weight distribution)

These are separate components that interact: the optimizer sets target weights, while the trading strategy generates entry/exit signals within those allocations.

## Project Structure

```
src/
  App.jsx                    # Root: BrowserRouter with route definitions
  main.jsx                   # Entry point: renders App into #root
  index.css                  # Tailwind v4 import + design system theme colors
  App.css                    # (empty - all styling via Tailwind)

  components/
    Layout.jsx               # Global shell: sidebar nav + top bar + content area
    KPICard.jsx              # Reusable KPI metric card with sparkline
    SignalBadge.jsx           # Colored pill badge for LONG/SHORT/EXIT/HOLD

  pages/
    Dashboard.jsx            # Landing page: combined overview of all 4 components
    Portfolio.jsx            # Portfolio Optimization: weights, frontier, sectors
    Monitoring.jsx           # Trading + Monitoring: signals, positions, risk
    AIInsights.jsx           # AI Explanations: trade explainer, summary, alerts, chat

  data/
    synthetic.js             # All placeholder data with schema documentation
```

## Page Details

### 1. Dashboard Overview (`/`)

The landing page providing a 30-second snapshot across all 4 components.

| Section | Component | Data Needed |
|---------|-----------|-------------|
| KPI: Total Portfolio Value | Portfolio Optimization | `portfolioValue` (number, USD) |
| KPI: Day P&L | Real-Time Monitoring | `dayPnL` (number, USD), `dayPnLPercent` (number, %) |
| KPI: Sharpe Ratio | Portfolio Optimization | `sharpeRatio` (number) |
| KPI: Active Positions | Algorithmic Trading | `positions.long`, `positions.short` (numbers) |
| Equity Curve | Real-Time Monitoring | `equityCurve[]` array: `{ date, portfolio, benchmark, drawdown }` |
| Portfolio Donut | Portfolio Optimization | `stocks[]` array: `{ ticker, weight }` |
| Recent Signals | Algorithmic Trading | `signals[]` array: `{ time, ticker, action, type, strength }` |
| AI Alerts | AI-Assisted Explanations | `alerts[]` array: `{ severity, time, title, message }` |

### 2. Portfolio Distribution (`/portfolio`)

Dedicated to the **Portfolio Optimization** component.

| Section | Data Needed |
|---------|-------------|
| Control Bar | Optimizer strategy list, last run timestamp |
| Allocation Treemap | `stocks[]`: `{ ticker, weight, sector }` |
| Efficient Frontier | `efficientFrontier[]`: `{ volatility, return }`, `individualStocks[]`, `currentPortfolio` |
| Optimization Summary | `sharpeRatio`, expected return %, portfolio vol %, max drawdown % |
| Allocation Table | `stocks[]`: all fields (ticker, name, weight, value, sector, price, change) |
| Sector Breakdown | `sectorBreakdown[]`: `{ name, value, color }` |
| Risk Contribution | `riskContribution[]`: `{ ticker, risk }` (sums to 100%) |
| Stock Detail Modal | Single stock object with all fields + historical metrics |

### 3. Live Monitoring (`/monitoring`)

Combines **Algorithmic Trading Strategies** and **Real-Time Monitoring**.

| Section | Component | Data Needed |
|---------|-----------|-------------|
| Status Bar | Both | `strategy_status`, `current_regime`, `update_interval` |
| KPI: Unrealized P&L | Monitoring | `monitoringKPIs.unrealizedPnL` (number, USD) |
| KPI: Realized P&L | Monitoring | `monitoringKPIs.realizedPnL` (number, USD) |
| KPI: Win Rate | Monitoring | `monitoringKPIs.winRate` (number, %) |
| KPI: Net Exposure | Monitoring | `monitoringKPIs.netExposure` (number, %) |
| Signal Feed | Trading | `signals[]`: `{ time, ticker, action, type, strength, detail }` |
| Position Tracker | Trading + Monitoring | `activePositions[]`: `{ ticker, direction, entry, current, pnl, pnlPercent, sl, tp }` |
| Equity Curve (Live) | Monitoring | `intradayEquity[]`: `{ time, value }` |
| Volatility Monitor | Monitoring | `volatilityMetrics`: `{ atr, vix, portfolioVol }` |
| Drawdown Tracker | Monitoring | `drawdownMetrics`: `{ current, maxToday, maxEver }` |
| Sector Exposure | Both | `sectorExposure[]`: `{ sector, exposure }` |
| Signal Detail Modal | Trading | Single signal object with all fields |

### 4. AI-Assisted Insights (`/ai-insights`)

Dedicated to the **AI-Assisted Explanations** component. Has 3 tabs + floating chat.

| Section | Tab | Data Needed |
|---------|-----|-------------|
| Trade Selector | Trade Explainer | List of recent signals as dropdown options |
| AI Explanation Card | Trade Explainer | `{ action, ticker, time, strategy, why[], risk, confidence }` |
| Trade History | Trade Explainer | `signals[]` with `.detail` field for AI annotations |
| Regime Indicator | Market Summary | `regime_label`, `regime_direction`, `regime_confidence` |
| AI Market Summary | Market Summary | AI-generated paragraph (from Claude API) |
| Key Observations | Market Summary | AI-generated bullet points (from Claude API) |
| Stock Heatmap | Market Summary | `heatmapData[]`: `{ ticker, change }` |
| Risk Alerts | Risk Alerts | `alerts[]`: `{ severity, time, title, message, recommendation }` |
| AI Chat Panel | (floating) | Conversation history `{ role, text }[]`, Claude API integration |

## Data Integration Guide

All placeholder data is in `src/data/synthetic.js`. Each export is documented with:
- Which **system component** it belongs to
- Which **page(s)** consume it
- What **backend source** should provide it
- The **data shape** with field descriptions

### To replace placeholder data with real sources:

1. **Create API service modules** (e.g., `src/api/portfolio.js`, `src/api/signals.js`)
2. **Replace imports** in each page from `../data/synthetic` to your API modules
3. **Use React state/effects** or a state manager (Zustand recommended) to fetch and store data
4. **For real-time data** (signals, positions, equity), set up WebSocket connections
5. **For AI features**, integrate the Anthropic SDK (Claude API) with appropriate system prompts

### Signal Type Codes

| Code | Full Name | Description |
|------|-----------|-------------|
| `LM` | Long Momentum | Enter long when momentum indicators signal upward trend |
| `SM` | Short Momentum | Enter short when strong downward momentum detected |
| `LR` | Long Reversion | Buy when price falls significantly below statistical range |
| `SR` | Short Reversion | Sell when price moves excessively above equilibrium range |
| `SL` | Stop-Loss | Exit triggered by stop-loss price hit |
| `TP` | Take-Profit | Exit triggered by take-profit target reached |

## Design System

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-main` | `#0D1117` | Page background |
| `bg-surface` | `#161B22` | Cards, panels |
| `bg-elevated` | `#1C2128` | Modals, dropdowns, hover states |
| `border` | `#30363D` | All borders |
| `text-primary` | `#E6EDF3` | Primary text |
| `text-secondary` | `#8B949E` | Secondary/muted text |
| `accent` | `#58A6FF` | Links, active states, accent |
| `profit` | `#3FB950` | Positive P&L, long positions |
| `loss` | `#F85149` | Negative P&L, short positions |
| `warning` | `#D29922` | Warning alerts |

### Typography

- **UI text**: Inter (loaded from Google Fonts)
- **Numbers/code**: JetBrains Mono (loaded from Google Fonts)

## Reusable Components

| Component | File | Props | Used By |
|-----------|------|-------|---------|
| `KPICard` | `components/KPICard.jsx` | `label`, `value`, `subtext`, `subtextColor`, `sparklineData` | Dashboard, Monitoring |
| `SignalBadge` | `components/SignalBadge.jsx` | `action` ('LONG'/'SHORT'/'EXIT'/'HOLD') | Dashboard, Monitoring, AI Insights |
| `Layout` | `components/Layout.jsx` | (none - wraps all pages) | App.jsx |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + Vite 8 |
| Styling | Tailwind CSS v4 |
| Charts | Recharts v3 |
| Icons | Lucide React |
| Routing | React Router v7 |

## Running Locally

```bash
npm install
npm run dev
```

The dev server will start at `http://localhost:5173` (or next available port).

## Next Steps for Integration

1. **Backend API**: Build REST/WebSocket endpoints for portfolio data, signals, positions
2. **State Management**: Add Zustand or React Context for global state
3. **WebSocket Feed**: Real-time updates for signals, positions, and equity curve
4. **Claude API**: Integrate Anthropic SDK for trade explanations, market summaries, and chat
5. **Responsive**: Tablet/mobile layouts (breakpoints defined in design spec)
