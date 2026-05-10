import React from 'react';
import { fetchCompile, type CompileResponse } from '../api/apiClient';
import Spinner from '../components/Spinner';

export default function CompilePane() {
  const [text, setText] = React.useState('');
  const [persist, setPersist] = React.useState(false);
  const [result, setResult] = React.useState<CompileResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetchCompile({ text, persist });
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
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 12 }}>Compile</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 12 }}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to compile..."
          rows={5}
          style={{
            background: '#030d20',
            border: '1px solid rgba(47,99,255,0.2)',
            borderRadius: 6,
            padding: 10,
            color: '#bfefff',
            fontSize: 12,
            fontFamily: 'var(--font)',
            outline: 'none',
            resize: 'vertical',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#5a7a9a', cursor: 'pointer' }}>
            <input type="checkbox" checked={persist} onChange={(e) => setPersist(e.target.checked)} style={{ accentColor: '#4f8cfb' }} />
            Persist
          </label>
          <button
            onClick={handleSubmit}
            disabled={!text.trim() || loading}
            style={{
              padding: '6px 14px',
              borderRadius: 5,
              border: '1px solid rgba(79,140,251,0.3)',
              background: 'rgba(79,140,251,0.15)',
              color: '#7fe0ff',
              fontSize: 12,
              fontFamily: 'var(--font)',
              cursor: 'pointer',
              opacity: !text.trim() || loading ? 0.5 : 1,
            }}
          >
            {loading ? <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Spinner /><span>Compiling...</span></span> : 'Compile'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: 10, borderRadius: 6, background: 'rgba(255,107,107,0.08)', border: '1px solid rgba(255,107,107,0.25)', color: '#ff6b6b', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#4f8cfb', marginBottom: 8 }}>Records</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {result.records.map((rec: any, idx: number) => (
              <div key={idx} style={{ background: '#020b1e', border: '1px solid rgba(47,99,255,0.12)', borderRadius: 6, padding: '8px 10px' }}>
                <div style={{ fontSize: 10, color: '#4f6888', marginBottom: 2 }}>{rec.id || `record-${idx}`} {rec.kind ? `- ${rec.kind}` : ''}</div>
                <div style={{ fontSize: 12, color: '#bfefff' }}>{rec.text || JSON.stringify(rec).slice(0, 200)}</div>
              </div>
            ))}
          </div>
          {result.persist && (
            <div style={{ marginTop: 8, padding: 10, borderRadius: 6, background: 'rgba(126,253,185,0.07)', border: '1px solid rgba(126,253,185,0.2)', color: '#7efdb9', fontSize: 11 }}>
              Persist successful
            </div>
          )}
        </div>
      )}
    </div>
  );
}
