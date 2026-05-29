import './ContextIndicator.css';

interface ContextIndicatorProps {
  usage: number;
}

function ContextIndicator({ usage }: ContextIndicatorProps) {
  const getColor = () => {
    if (usage > 80) return '#ef4444'; // red
    if (usage > 50) return '#f59e0b'; // orange
    return '#10b981'; // green
  };

  return (
    <div className="context-indicator">
      <span className="label">Context:</span>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{
            width: `${Math.min(usage, 100)}%`,
            backgroundColor: getColor(),
          }}
        />
      </div>
      <span className="percentage">{usage.toFixed(0)}%</span>
      {usage > 80 && <span className="warning">⚠ Zusammenfassung läuft...</span>}
    </div>
  );
}

export default ContextIndicator;
