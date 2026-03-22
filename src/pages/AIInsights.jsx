// =============================================================================
// PAGE: AI-ASSISTED INSIGHTS
// ROUTE: /ai-insights
// =============================================================================
// PRIMARY COMPONENT: AI-Assisted Explanations
//
// This page provides AI-powered interpretability features:
//   - Trade Explainer: why a specific trade was entered or exited
//   - Market Summary: AI-generated overview of current market conditions
//   - Risk Alerts: AI-generated risk warnings and recommendations
//   - AI Chat: floating conversational interface for ad-hoc questions
//
// TAB LAYOUT:
// +----------------------------------------------+
// | TAB BAR: [Trade Explainer] [Market Summary]  |
// |          [Risk Alerts]                       |
// +----------------------------------------------+
// |                                              |
// | TAB CONTENT (varies by active tab)           |
// |                                              |
// +----------------------------------------------+
// | [AI CHAT BUTTON - floating bottom-right]     |  <- Always visible
// +----------------------------------------------+
//
// AI INTEGRATION:
//   All AI-generated content on this page should come from the Claude API
//   (or equivalent LLM). The current placeholder text shows the expected
//   FORMAT and STRUCTURE of AI responses. Replace with actual API calls.
// =============================================================================

import { useState } from 'react';
import { signals, alerts } from '../data/synthetic';
import SignalBadge from '../components/SignalBadge';
import { Bot, AlertTriangle, Info, Send, RefreshCw } from 'lucide-react';

const tabs = ['Trade Explainer', 'Market Summary', 'Risk Alerts'];
const alertFilters = ['All', 'Critical', 'Warning', 'Info'];

// -----------------------------------------------------------------------------
// TRADE EXPLANATIONS (AI-generated)
// COMPONENT: AI-Assisted Explanations
// SOURCE: Claude API / LLM - given a signal object, generate an explanation
// DATA SHAPE per explanation:
//   - action {string}: trading action (LONG/SHORT/EXIT)
//   - ticker {string}: stock symbol
//   - time {string}: exact timestamp
//   - strategy {string}: full strategy name
//   - why {string[]}: array of reasons (numbered list in UI)
//   - risk {string}: risk assessment paragraph
//   - confidence {number|null}: 0-1 confidence score (null for exits)
//
// TO INTEGRATE: Call AI API with the signal data + indicator snapshot
//   and parse the response into this structure.
// -----------------------------------------------------------------------------
const tradeExplanations = {
  'LONG AAPL 10:32': {
    action: 'LONG', ticker: 'AAPL', time: '10:32:14 AM', strategy: 'Long Momentum (LM)',
    why: [
      'MACD Crossover: The MACD line crossed above the signal line at 1.24, with an expanding histogram indicating growing bullish momentum.',
      'Bollinger Band Position: Price ($183.42) moved above the mid-band ($180.15), confirming the upward trend direction.',
      'Volatility Check: ATR (3.21) is within the normal range, meaning the breakout is happening in stable conditions rather than during a volatility spike.',
    ],
    risk: 'Stop-loss set at $177.80 (-3.1%), giving a risk-reward ratio of 1:1.6 with the take-profit target at $192.60.',
    confidence: 0.82,
  },
  'EXIT TSLA 10:15': {
    action: 'EXIT', ticker: 'TSLA', time: '10:15:22 AM', strategy: 'Stop-Loss (SL)',
    why: [
      'Stop-loss triggered at $241.20 after a sudden price reversal.',
      'Volatility spiked to 2.1x the 20-day average ATR, invalidating the original entry thesis.',
      'MACD histogram turned sharply negative, confirming the momentum shift.',
    ],
    risk: 'Position closed with a realized loss of -$1,820 (-2.1%). The tightened stop-loss (from -3.5% to -2.0%) limited further damage.',
    confidence: null,
  },
  'SHORT META 09:45': {
    action: 'SHORT', ticker: 'META', time: '09:45:08 AM', strategy: 'Short Reversion (SR)',
    why: [
      'Price reached the upper Bollinger Band at $542.30, which is 2.1 standard deviations above the 20-day mean.',
      'Declining MACD histogram signals weakening upward momentum despite elevated prices.',
      'Historical pattern: META has reverted from similar overbought levels in 7 of the last 10 instances.',
    ],
    risk: 'Stop-loss at $558.80 (+3.0%), take-profit at $515.40 (-5.0%). Risk-reward ratio of 1:1.67.',
    confidence: 0.65,
  },
};

// -----------------------------------------------------------------------------
// AI CHAT MESSAGES (conversation history)
// COMPONENT: AI-Assisted Explanations
// SOURCE: Claude API - streaming conversation
// DATA SHAPE per message:
//   - role {string}: 'ai' | 'user'
//   - text {string}: message content
// TO INTEGRATE: Use Anthropic SDK with conversation context including
//   portfolio state, active positions, and recent signals.
// -----------------------------------------------------------------------------
const chatMessages = [
  { role: 'ai', text: 'Good morning! The portfolio is performing well today with +1.01% return. 7 long and 3 short positions are active. The current regime is TRENDING (Bullish).' },
  { role: 'user', text: 'Why did we short META?' },
  { role: 'ai', text: 'META was shorted at 09:45 AM using the Short Reversion (SR) strategy. The price reached the upper Bollinger Band at $542.30, which is 2.1 standard deviations above the 20-day mean. Combined with a declining MACD histogram, this signals overbought conditions likely to revert.' },
  { role: 'user', text: "What's our biggest risk right now?" },
  { role: 'ai', text: 'Your largest risk exposure is TSLA. Despite being only 7.2% of portfolio weight, it contributes 18% of total risk due to elevated volatility (ATR 2.1x normal). The system has already reduced position size by 40% and tightened the stop-loss.' },
];

// -----------------------------------------------------------------------------
// STOCK HEATMAP DATA
// COMPONENT: AI-Assisted Explanations (Market Summary tab)
// SOURCE: Market data feed - today's price change per stock
// DATA SHAPE: { ticker {string}, change {number} % change today }
// COLORS: Green intensity = positive change, Red intensity = negative change
// -----------------------------------------------------------------------------
const heatmapData = [
  { ticker: 'AAPL', change: 1.4 }, { ticker: 'MSFT', change: 0.8 }, { ticker: 'NVDA', change: 2.1 },
  { ticker: 'GOOGL', change: 0.5 }, { ticker: 'AMZN', change: 0.9 }, { ticker: 'META', change: -0.3 },
  { ticker: 'TSLA', change: -1.2 }, { ticker: 'BRK.B', change: 0.2 }, { ticker: 'JPM', change: -0.4 },
  { ticker: 'UNH', change: 0.1 },
];

const alertIcons = {
  critical: <AlertTriangle size={16} className="text-loss" />,
  warning: <AlertTriangle size={16} className="text-warning" />,
  info: <Info size={16} className="text-accent" />,
};

const alertStyles = {
  critical: 'border-l-loss bg-loss/5',
  warning: 'border-l-warning bg-warning/5',
  info: 'border-l-accent bg-accent/5',
};

export default function AIInsights() {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedTrade, setSelectedTrade] = useState(Object.keys(tradeExplanations)[0]);
  const [alertFilter, setAlertFilter] = useState('All');

  const explanation = tradeExplanations[selectedTrade];
  const filteredAlerts = alertFilter === 'All'
    ? alerts
    : alerts.filter(a => a.severity === alertFilter.toLowerCase());

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-text-primary">AI-Assisted Insights</h1>

      {/* ================================================================
          TAB BAR
          PURPOSE: Switch between the 3 AI feature tabs.
          ================================================================ */}
      <div className="flex gap-1 bg-bg-surface border border-border rounded-lg p-1">
        {tabs.map((tab, i) => (
          <button
            key={tab}
            onClick={() => setActiveTab(i)}
            className={`flex-1 py-2 px-4 rounded text-sm font-medium transition-colors ${
              activeTab === i
                ? 'bg-accent/15 text-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ================================================================
          TAB 1: TRADE EXPLAINER
          COMPONENT: AI-Assisted Explanations
          PURPOSE: Explains WHY a specific trade was entered or exited.
                   The AI analyzes the technical indicators at the time of
                   the signal and provides a human-readable explanation.
          SECTIONS:
            1. Trade selector dropdown (pick from recent signals)
            2. AI explanation card (reasons, risk assessment, confidence)
            3. Trade history with AI-annotated summaries
          DATA FLOW: User selects trade -> AI generates explanation
          ================================================================ */}
      {activeTab === 0 && (
        <div className="space-y-4">

          {/* TRADE SELECTOR
              DATA: List of recent signals formatted as "<action> <ticker> <time>"
              TODO: Populate from signals[] dynamically */}
          <div className="bg-bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <span className="text-text-secondary text-sm">Select Trade:</span>
              <select
                value={selectedTrade}
                onChange={e => setSelectedTrade(e.target.value)}
                className="bg-bg-elevated border border-border rounded px-3 py-1.5 text-text-primary text-sm flex-1"
              >
                {Object.keys(tradeExplanations).map(k => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>
          </div>

          {/* AI EXPLANATION CARD
              TEMPLATE STRUCTURE:
                [AI Icon] Trade Explanation
                [ACTION_BADGE] <ticker> | Time: <time> | Strategy: <strategy_name>

                WHY THIS TRADE WAS ENTERED/EXITED:
                1. <reason_1> (indicator reading + interpretation)
                2. <reason_2>
                3. <reason_3>

                RISK ASSESSMENT:
                <risk_paragraph>

                CONFIDENCE: <confidence_score>/1.00 [progress bar]

              TO INTEGRATE: Send signal data to Claude API, parse response. */}
          {explanation && (
            <div className="bg-bg-surface border border-border rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Bot size={20} className="text-accent" />
                <span className="text-text-primary font-semibold">Trade Explanation</span>
              </div>

              {/* Trade header: action badge + metadata */}
              <div className="flex items-center gap-3 mb-4">
                <SignalBadge action={explanation.action} />
                <span className="text-text-primary font-semibold">{explanation.ticker}</span>
                <span className="text-text-secondary text-sm">Time: {explanation.time}</span>
                <span className="text-text-secondary text-sm">Strategy: {explanation.strategy}</span>
              </div>

              {/* Numbered reasons list (AI-generated) */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-text-secondary uppercase mb-2">Why This Trade Was {explanation.action === 'EXIT' ? 'Exited' : 'Entered'}</h3>
                <ol className="space-y-2">
                  {explanation.why.map((reason, i) => (
                    <li key={i} className="text-text-primary text-sm leading-relaxed flex gap-2">
                      <span className="text-accent font-semibold shrink-0">{i + 1}.</span>
                      {reason}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Risk assessment (AI-generated) */}
              <div className="bg-bg-elevated border border-border/50 rounded-lg p-3 mb-4">
                <h3 className="text-xs font-semibold text-text-secondary uppercase mb-1">Risk Assessment</h3>
                <p className="text-text-primary text-sm">{explanation.risk}</p>
              </div>

              {/* Confidence score (from signal strength, visualized as progress bar) */}
              {explanation.confidence && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-secondary">Confidence</span>
                    <span className="text-text-primary font-mono">High ({explanation.confidence.toFixed(2)}/1.00)</span>
                  </div>
                  <div className="h-2.5 bg-bg-main rounded-full overflow-hidden">
                    <div className="h-full bg-accent rounded-full" style={{ width: `${explanation.confidence * 100}%` }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TRADE HISTORY (AI-annotated)
              PURPOSE: Shows recent trades with short AI-generated summaries.
              DATA: signals[] array (most recent 5), each signal's .detail
                    field contains the AI annotation.
              TEMPLATE per entry:
                <time> [ACTION_BADGE] <ticker>
                "<ai_summary_text>..." */}
          <div className="bg-bg-surface border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Trade History (AI Annotated)</h3>
            <div className="space-y-3">
              {signals.slice(0, 5).map((s, i) => (
                <div key={i} className="flex gap-3 py-2 border-b border-border/30 last:border-0">
                  <span className="text-text-secondary text-xs font-mono shrink-0 w-10 pt-0.5">{s.time}</span>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <SignalBadge action={s.action} />
                      <span className="text-text-primary text-sm font-semibold">{s.ticker}</span>
                    </div>
                    <p className="text-text-secondary text-xs italic">"{s.detail.substring(0, 80)}..."</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ================================================================
          TAB 2: MARKET SUMMARY
          COMPONENT: AI-Assisted Explanations
          PURPOSE: AI-generated overview of current market conditions,
                   regime classification, and per-stock performance heatmap.
          SECTIONS:
            1. Overall regime indicator with confidence bar
            2. AI-written market summary paragraph
            3. Key observations (bullet points)
            4. Stock heatmap grid (5x2 colored tiles)
            5. Auto-refresh controls
          DATA NEEDED (for AI generation):
            - Current regime classification + confidence %
            - All stock prices and % changes today
            - Technical indicator readings across portfolio
            - VIX and market-wide metrics
          TO INTEGRATE: Periodically call Claude API with portfolio snapshot
            to generate this summary. Cache and refresh on interval.
          ================================================================ */}
      {activeTab === 1 && (
        <div className="space-y-4">
          <div className="bg-bg-surface border border-border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <Bot size={20} className="text-accent" />
              {/* DATA: {string} current_date */}
              <span className="text-text-primary font-semibold">Market Summary - March 20, 2026</span>
              {/* DATA: {string} generation_timestamp */}
              <span className="text-text-secondary text-xs ml-auto">Generated at 11:00 AM ET</span>
            </div>

            {/* REGIME INDICATOR
                DATA:
                  - regime_label {string}: 'TRENDING' | 'MEAN-REVERTING'
                  - regime_direction {string}: 'Bullish' | 'Bearish' | 'Neutral'
                  - regime_confidence {number}: 0-100% */}
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-text-secondary text-sm">Overall Regime:</span>
                <span className="text-accent font-semibold">TRENDING (Bullish)</span>
              </div>
              <div className="h-2.5 bg-bg-main rounded-full overflow-hidden mb-1">
                <div className="h-full bg-accent rounded-full" style={{ width: '78%' }} />
              </div>
              <span className="text-text-secondary text-xs">78% confidence</span>
            </div>

            {/* AI-GENERATED SUMMARY
                DATA: {string} ai_market_summary - paragraph from Claude API */}
            <div className="mb-4">
              <h3 className="text-xs font-semibold text-text-secondary uppercase mb-2">Summary</h3>
              <p className="text-text-primary text-sm leading-relaxed">
                Markets are showing sustained upward momentum this morning. 7 of 10 tracked stocks are trading above their 20-day moving averages.
                The VIX remains subdued at 18.2, supporting the current bullish positioning. The system has maintained its net-long bias with 78% exposure.
              </p>
            </div>

            {/* AI-GENERATED KEY OBSERVATIONS
                DATA: {string[]} observations - bullet points from Claude API */}
            <div className="mb-4">
              <h3 className="text-xs font-semibold text-text-secondary uppercase mb-2">Key Observations</h3>
              <ul className="space-y-1.5 text-sm text-text-primary">
                <li className="flex gap-2"><span className="text-accent">-</span> Tech sector leading with NVDA (+2.1%) and AAPL (+1.4%) showing strong momentum</li>
                <li className="flex gap-2"><span className="text-accent">-</span> Financials lagging; JPM showing mean-reversion signals near lower Bollinger Band</li>
                <li className="flex gap-2"><span className="text-accent">-</span> TSLA volatility elevated (ATR 2x avg), system reducing position size</li>
              </ul>
            </div>

            {/* STOCK HEATMAP
                DATA: heatmapData[] - ticker + today's % change
                COLORS: Green intensity proportional to positive change,
                        red intensity proportional to negative change.
                LAYOUT: 5 columns x 2 rows grid */}
            <div>
              <h3 className="text-xs font-semibold text-text-secondary uppercase mb-2">Stock Heatmap</h3>
              <div className="grid grid-cols-5 gap-1.5">
                {heatmapData.map(s => (
                  <div
                    key={s.ticker}
                    className="rounded-lg p-3 text-center"
                    style={{
                      backgroundColor: s.change >= 0
                        ? `rgba(63, 185, 80, ${Math.min(0.3, Math.abs(s.change) * 0.15)})`
                        : `rgba(248, 81, 73, ${Math.min(0.3, Math.abs(s.change) * 0.15)})`,
                    }}
                  >
                    <div className="text-text-primary text-sm font-semibold">{s.ticker}</div>
                    <div className={`text-xs font-mono ${s.change >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {s.change >= 0 ? '+' : ''}{s.change}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* REFRESH CONTROLS
              PURPOSE: Control how often the AI market summary regenerates.
              TODO: Wire auto-refresh interval to trigger periodic API calls.
              TODO: Wire "Refresh Now" button to trigger immediate API call. */}
          <div className="bg-bg-surface border border-border rounded-lg px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-text-secondary text-sm">Auto-refresh:</span>
              <select className="bg-bg-elevated border border-border rounded px-2 py-1 text-text-primary text-xs">
                <option>Every 15 min</option>
                <option>Every 30 min</option>
                <option>Every 1 hour</option>
              </select>
            </div>
            <button className="flex items-center gap-1.5 text-accent text-sm hover:underline">
              <RefreshCw size={14} /> Refresh Now
            </button>
          </div>
        </div>
      )}

      {/* ================================================================
          TAB 3: RISK ALERTS
          COMPONENT: AI-Assisted Explanations
          PURPOSE: AI-generated alerts when risk conditions change.
                   Alerts are triggered by:
                   - Volatility spikes (ATR exceeds threshold)
                   - Drawdown warnings (approaching limits)
                   - Rebalance suggestions (drift from optimal)
                   - Strategy state changes
          DATA: alerts[] array, each with:
            - severity {string}: 'critical' | 'warning' | 'info'
            - time {string}: when alert was generated
            - title {string}: short headline
            - message {string}: AI-generated explanation
            - recommendation {string|null}: AI's suggested action
          FILTERS: All / Critical / Warning / Info
          STYLING:
            - Critical: red left border, red icon, red-tinted bg
            - Warning: amber left border, amber icon, amber-tinted bg
            - Info: blue left border, blue icon, blue-tinted bg
          ================================================================ */}
      {activeTab === 2 && (
        <div className="space-y-4">
          {/* Alert severity filter buttons */}
          <div className="flex gap-2">
            {alertFilters.map(f => (
              <button
                key={f}
                onClick={() => setAlertFilter(f)}
                className={`px-3 py-1.5 rounded text-sm ${
                  alertFilter === f
                    ? 'bg-accent/15 text-accent'
                    : 'bg-bg-surface text-text-secondary hover:text-text-primary border border-border'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Alert cards */}
          <div className="space-y-3">
            {filteredAlerts.map((a, i) => (
              <div key={i} className={`border-l-2 rounded-r-lg p-4 bg-bg-surface border border-border ${alertStyles[a.severity]}`}>
                <div className="flex items-center gap-2 mb-2">
                  {alertIcons[a.severity]}
                  <span className="text-text-primary text-sm font-semibold">{a.title}</span>
                  <span className="text-text-secondary text-xs ml-auto">{a.time}</span>
                </div>
                {/* AI-generated alert message */}
                <p className="text-text-primary text-sm leading-relaxed mb-2">{a.message}</p>
                {/* AI-generated recommendation (if any) */}
                {a.recommendation && (
                  <p className="text-text-secondary text-xs italic">Recommendation: {a.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================================================================
          AI CHAT PANEL (floating, accessible from any tab)
          COMPONENT: AI-Assisted Explanations
          PURPOSE: Conversational interface for ad-hoc questions about
                   trades, portfolio, market conditions, etc.
          BEHAVIOR:
            - Floating button (bottom-right) toggles the panel
            - Chat history displayed as message bubbles
            - User types question, AI responds in context
          DATA:
            - chatMessages[]: conversation history { role, text }
          TO INTEGRATE:
            - Use Anthropic SDK for streaming responses
            - Include system prompt with portfolio state, active positions,
              recent signals, and risk metrics as context
            - Support questions like:
              "Why did we short META?"
              "What's our biggest risk?"
              "Should I rebalance?"
          ================================================================ */}
      <AIChat />
    </div>
  );
}

// =============================================================================
// AI CHAT COMPONENT (floating panel)
// =============================================================================
function AIChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');

  return (
    <>
      {/* Chat toggle button - always visible at bottom-right */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-12 h-12 bg-accent rounded-full flex items-center justify-center shadow-lg hover:bg-accent/80 transition-colors z-50"
      >
        <Bot size={22} className="text-bg-main" />
      </button>

      {/* Chat panel - slides in when open */}
      {open && (
        <div className="fixed bottom-20 right-6 w-96 h-[500px] bg-bg-surface border border-border rounded-xl shadow-2xl flex flex-col z-50">
          {/* Chat header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-accent" />
              <span className="text-text-primary text-sm font-semibold">AI Assistant</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-text-secondary hover:text-text-primary">&times;</button>
          </div>

          {/* Message history
              TEMPLATE per message:
                AI messages: left-aligned, dark bg, border
                User messages: right-aligned, accent-tinted bg */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-accent/15 text-text-primary'
                    : 'bg-bg-elevated text-text-primary border border-border/50'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          {/* Input area
              TODO: Wire to Claude API via Anthropic SDK
              TODO: Add loading state while AI is generating response
              TODO: Stream AI response tokens for real-time display */}
          <div className="border-t border-border p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Type a question..."
                className="flex-1 bg-bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-accent"
              />
              <button className="bg-accent text-bg-main p-2 rounded-lg hover:bg-accent/80">
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
