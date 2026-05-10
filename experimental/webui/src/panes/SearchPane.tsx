import React from 'react';
import { fetchSearch, type SearchResponse } from '../api/apiClient';
import Spinner from '../components/Spinner';

export default function SearchPane() {
  const [query, setQuery] = React.useState('');
  const [budget, setBudget] = React.useState(5);
  const [result, setResult] = React.useState<SearchResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetchSearch(query, budget);
      setResult(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if ((e as Error & { code?: string }).code === 'DISCONNECTED') {
        setError('Cannot reach the SEAM API. Is the server running?');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16, overflowY: 'auto', flex: 1 }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 12 }}>Search</div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search query..."
          style={{
            flex: 1,
            minWidth: 200,
            background: '#030d20',
            border: '1px solid rgba(47,99,255,0.2)',
            borderRadius: 6,
            padding: '8px 10px',
            color: '#bfefff',
            fontSize: 12,
            fontFamily: 'var(--font)',
            outline: 'none',
          }}
        />
        <input
          type="number"
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          min={1}
          max={100}
          style={{
            width: 72,
            background: '#030d20',
            border: '1px solid rgba(47,99,255,0.2)',
            borderRadius: 6,
            padding: '8px 10px',
            color: '#bfefff',
            fontSize: 12,
            fontFamily: 'var(--font)',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!query.trim() || loading}
          style={{
            padding: '6px 14px',
            borderRadius: 5,
            border: '1px solid rgba(79,140,251,0.3)',
            background: 'rgba(79,140,251,0.15)',
            color: '#7fe0ff',
            fontSize: 12,
            fontFamily: 'var(--font)',
            cursor: 'pointer',
            opacity: !query.trim() || loading ? 0.5 : 1,
          }}
        >
          {loading ? <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Spinner /><span>Searching...</span></span> : 'Search'}
        </button>
      </div>

      {error && (
        <div style={{ padding: 10, borderRadius: 6, background: 'rgba(255,107,107,0.08)', border: '1px solid rgba(255,107,107,0.25)', color: '#ff6b6b', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 8 }}>Candidates</div>
          {result.candidates.map((c, idx) => (
            <div key={idx} style={{ background: '#020b1e', border: '1px solid rgba(47,99,255,0.12)', borderRadius: 6, padding: '8px 10px', marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ fontSize: 10, color: '#4f6888' }}>{c.record.id} {c.record.kind ? `- ${c.record.kind}` : ''}</span>
                <span style={{ fontSize: 10, color: '#7efdb9' }}>score {c.score.toFixed(3)}</span>
              </div>
              <div style={{ fontSize: 12, color: '#bfefff' }}>{c.record.text || JSON.stringify(c.record).slice(0, 200)}</div>
            </div>
          ))}
          {result.candidates.length === 0 && (
            <div style={{ color: '#5a7a9a', fontSize: 12 }}>No results</div>
          )}
        </div>
      )}
    </div>
  );
}
