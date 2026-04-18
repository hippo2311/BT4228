// =============================================================================
// LAYOUT COMPONENT - Global Shell
// =============================================================================
// This is the root layout wrapping all pages. It provides:
//   1. SIDEBAR NAVIGATION - icon-only nav linking to the 4 main pages
//   2. TOP BAR - app title, live status indicator, clock
//   3. MAIN CONTENT AREA - where each page renders via <Outlet />
//
// STRUCTURE:
// +--------+-------------------------------------------------+
// | SIDE   | TOP BAR (logo, live status, clock)              |
// | NAV    +-------------------------------------------------+
// | (64px) | MAIN CONTENT AREA (<Outlet /> = current page)   |
// |  [D]   |                                                 |
// |  [P]   |                                                 |
// |  [M]   |                                                 |
// |  [AI]  |                                                 |
// +--------+-------------------------------------------------+
//
// NAVIGATION PAGES:
//   [D]  = Dashboard Overview   (/)            - combined overview of all 4 components
//   [P]  = Portfolio Distribution (/portfolio) - PORTFOLIO OPTIMIZATION component
//   [M]  = Live Monitoring       (/monitoring) - ALGORITHMIC TRADING + REAL-TIME MONITORING
//   [AI] = AI Insights           (/ai-insights)- AI-ASSISTED EXPLANATIONS component
// =============================================================================

import { createElement, useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, PieChart, Activity, Bot } from 'lucide-react';
import { fetchStatus, LIVE_POLL_MS } from '../services/api';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/portfolio', icon: PieChart, label: 'Portfolio' },
  { to: '/monitoring', icon: Activity, label: 'Monitoring' },
  { to: '/ai-insights', icon: Bot, label: 'AI Insights' },
];

export default function Layout() {
  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  );
  const [backendStatus, setBackendStatus] = useState('loading');

  useEffect(() => {
    const tickClock = () => {
      setClock(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    tickClock();
    const clockId = setInterval(tickClock, 1000);
    return () => clearInterval(clockId);
  }, []);

  useEffect(() => {
    const syncStatus = () => {
      fetchStatus()
        .then((status) => setBackendStatus(status.status || 'loading'))
        .catch(() => setBackendStatus('error'));
    };

    syncStatus();
    const statusId = setInterval(syncStatus, LIVE_POLL_MS);
    return () => clearInterval(statusId);
  }, []);

  const liveTone = backendStatus === 'ready'
    ? 'bg-profit text-profit'
    : backendStatus === 'loading'
      ? 'bg-warning text-warning'
      : 'bg-loss text-loss';
  const liveLabel = backendStatus === 'ready'
    ? 'LIVE'
    : backendStatus === 'loading'
      ? 'SYNCING'
      : 'OFFLINE';

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ================================================================
          SIDEBAR NAVIGATION (64px wide, icon-only)
          - Collapsed by default; hover shows tooltip with page name
          - Active page: blue left accent bar + filled icon
          ================================================================ */}
      <nav className="w-16 bg-bg-surface border-r border-border flex flex-col items-center py-4 gap-2 shrink-0">
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group relative w-12 h-12 flex items-center justify-center rounded-lg transition-colors ${
                isActive
                  ? 'bg-accent/15 text-accent border-l-2 border-accent'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
              }`
            }
          >
            {createElement(icon, { size: 20 })}
            {/* Tooltip on hover */}
            <span className="absolute left-14 bg-bg-elevated text-text-primary text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
              {label}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Main area (top bar + content) */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* ================================================================
            TOP BAR (56px height)
            - Left:  App logo/name
            - Right: Live status indicator (green pulsing dot) + current time
            DATA NEEDED:
              - {boolean} isLive - whether the system is connected/running
              - {string}  currentTime - real-time clock (auto-updating)
            ================================================================ */}
        <header className="h-14 bg-bg-surface border-b border-border flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-3">
            <Activity size={20} className="text-accent" />
            <span className="font-semibold text-text-primary text-sm">TradeX: A Regime-Adaptive QTS</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${liveTone.split(' ')[0]} ${backendStatus === 'ready' ? 'animate-pulse' : ''}`} />
              <span className={`${liveTone.split(' ')[1]} font-medium`}>{liveLabel}</span>
            </span>
            <span className="text-text-secondary text-xs font-mono">
              {clock}
            </span>
          </div>
        </header>

        {/* ================================================================
            MAIN CONTENT AREA
            - Scrollable container where each page renders
            - <Outlet /> is replaced by the matched route's component
            ================================================================ */}
        <main className="flex-1 overflow-y-auto p-6 bg-bg-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
