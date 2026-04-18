// ── API client for the Flask backend ─────────────────────────────────────────
// Local development uses /api/* via the Vite proxy.
// Production can point to a real backend with VITE_API_BASE_URL.

const RAW_BASE = import.meta.env.VITE_API_BASE_URL?.trim();
const BASE = RAW_BASE ? RAW_BASE.replace(/\/$/, '') : '/api';
export const LIVE_POLL_MS = 5_000;

async function get(path) {
  const res = await fetch(BASE + path, {
    cache: 'no-store',
    headers: { 'Cache-Control': 'no-cache' },
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

/** Returns status of the backend data loader: "loading" | "ready" | "error" */
export const fetchStatus     = ()              => get('/status');

/** All data for the Dashboard page */
export const fetchDashboard  = ()              => get('/dashboard');

/** Portfolio allocation, efficient frontier, stock metrics */
export const fetchPortfolio  = ()              => get('/portfolio');

/** Monitoring: positions, signals, KPIs, drawdown, sector exposure */
export const fetchMonitoring = ()              => get('/monitoring');

/** AI-generated risk alerts */
export const fetchAlerts     = ()              => get('/alerts');

/** Ask the OpenAI assistant to explain a specific trading signal */
export const explainTrade    = (signal)        => post('/ai/explain', { signal });

/** Ask the OpenAI assistant for a market summary given current portfolio state */
export const getMarketSummary = ()             => post('/ai/summary', {});

/** Send a chat message to the OpenAI assistant */
export const chatMessage      = (message, history = []) =>
  post('/ai/chat', { message, history });

/** Trigger a fresh data reload on the backend */
export const refreshData      = ()             => post('/refresh', {});
