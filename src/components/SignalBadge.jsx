// =============================================================================
// SIGNAL BADGE - Reusable Trading Action Badge Component
// =============================================================================
// Displays a colored pill badge indicating a trading action type.
// Used in signal feed tables, position tracker cards, and trade explanations.
//
// COMPONENT: Algorithmic Trading Strategies
//
// PROPS:
//   - action: {string} One of: 'LONG' | 'SHORT' | 'EXIT' | 'HOLD'
//
// VISUAL VARIANTS:
//   [LONG]   -> Green background, green text  (entering long position)
//   [SHORT]  -> Red background, red text      (entering short position)
//   [EXIT]   -> Gray background, gray text    (closing a position)
//   [HOLD]   -> Blue outline, blue text       (maintaining position)
// =============================================================================

export default function SignalBadge({ action }) {
  const styles = {
    LONG: 'bg-profit/20 text-profit',
    SHORT: 'bg-loss/20 text-loss',
    EXIT: 'bg-neutral/20 text-neutral',
    HOLD: 'border border-accent text-accent bg-transparent',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${styles[action] || styles.HOLD}`}>
      {action}
    </span>
  );
}
