import React from 'react';

interface StatusBarProps {
  connected: boolean;
  health: { status: string; store_path: string } | null;
  error: string | null;
}

export default function StatusBar({ connected, health, error }: StatusBarProps) {
  const [time, setTime] = React.useState(new Date());
  React.useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const fmt = (d: Date) => d.toLocaleTimeString('en-US', { hour12: false });

  return (
    <div
      style={{
        height: 24,
        background: '#020b1f',
        borderTop: '1px solid rgba(47,99,255,0.25)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        gap: 16,
        fontSize: 11,
        color: '#4f8cfb',
        flexShrink: 0,
      }}
    >
      <span style={{ color: connected ? '#7efdb9' : '#ff6b6b', display: 'flex', alignItems: 'center', gap: 5 }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: connected ? '#7efdb9' : '#ff6b6b',
            display: 'inline-block',
            boxShadow: connected ? '0 0 6px #7efdb9' : '0 0 6px #ff6b6b',
          }}
        />
        {connected ? 'API connected' : 'Disconnected'}
      </span>
      {error && <span style={{ color: '#ff6b6b' }}>{error}</span>}
      {health && <span style={{ color: '#5a7a9a' }}>{health.store_path}</span>}
      <div style={{ flex: 1 }} />
      <span style={{ color: '#7fe0ff' }}>{fmt(time)}</span>
    </div>
  );
}
