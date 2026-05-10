import React from 'react';
import { fetchHealth, fetchStats, type HealthResponse, type StatsResponse } from '../api/apiClient';
import Spinner from '../components/Spinner';

export default function StatusPane() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [stats, setStats] = React.useState<StatsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [statsError, setStatsError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const h = await fetchHealth();
        if (!mounted) return;
        setHealth(h);
        setError(null);
        try {
          const s = await fetchStats();
          if (!mounted) return;
          setStats(s);
          setStatsError(null);
        } catch (e) {
          if (!mounted) return;
          const msg = e instanceof Error ? e.message : String(e);
          if ((e as Error & { code?: string }).code === 'UNAUTHORIZED') {
            setStatsError('Unauthorized - set bearer token in Settings.');
          } else {
            setStatsError(msg);
          }
        }
      } catch (e) {
        if (!mounted) return;
        const msg = e instanceof Error ? e.message : String(e);
        if ((e as Error & { code?: string }).code === 'DISCONNECTED') {
          setError('Cannot reach the SEAM API. Is the server running?');
        } else {
          setError(msg);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <div style={{ padding: 16, overflowY: 'auto', flex: 1 }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 12 }}>API Health</div>
      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#5a7a9a' }}>
          <Spinner />
          <span>Checking health...</span>
        </div>
      )}
      {error && !loading && (
        <div style={{ padding: 10, borderRadius: 6, background: 'rgba(255,107,107,0.08)', border: '1px solid rgba(255,107,107,0.25)', color: '#ff6b6b', fontSize: 12 }}>
          {error}
        </div>
      )}
      {health && !loading && (
        <div style={{ padding: 12, borderRadius: 6, background: 'rgba(126,253,185,0.08)', border: '1px solid rgba(126,253,185,0.25)', marginBottom: 16 }}>
          <div style={{ color: '#7efdb9', fontSize: 12, marginBottom: 4 }}>Status: {health.status}</div>
          <div style={{ color: '#5a7a9a', fontSize: 11 }}>Store: {health.store_path}</div>
        </div>
      )}

      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 12 }}>Stats</div>
      {statsError && (
        <div style={{ padding: 10, borderRadius: 6, background: 'rgba(244,214,118,0.08)', border: '1px solid rgba(244,214,118,0.25)', color: '#f4d676', fontSize: 12 }}>
          {statsError}
        </div>
      )}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {Object.entries(stats).slice(0, 12).map(([k, v]) => (
            <div key={k} style={{ background: '#020b1e', border: '1px solid rgba(47,99,255,0.12)', borderRadius: 6, padding: '8px 10px' }}>
              <div style={{ fontSize: 9, color: '#4f6888', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 3 }}>{k}</div>
              <div style={{ fontSize: 13, color: '#7fe0ff', fontWeight: 500 }}>{String(v)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
