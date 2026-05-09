import React from 'react';
import ActivityBar from './components/ActivityBar';
import StatusBar from './components/StatusBar';
import StatusPane from './panes/StatusPane';
import CompilePane from './panes/CompilePane';
import SearchPane from './panes/SearchPane';
import ContextPane from './panes/ContextPane';
import SettingsPane from './panes/SettingsPane';
import type { PaneId } from './components/ActivityBar';
import { fetchHealth } from './api/apiClient';
import './index.css';

const PANES: Record<PaneId, React.FC> = {
  status: StatusPane,
  compile: CompilePane,
  search: SearchPane,
  context: ContextPane,
  settings: SettingsPane,
};

export default function App() {
  const [activePane, setActivePane] = React.useState<PaneId>('status');
  const [connected, setConnected] = React.useState(false);
  const [health, setHealth] = React.useState<{ status: string; store_path: string } | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const h = await fetchHealth();
        if (!mounted) return;
        setConnected(true);
        setHealth(h);
        setError(null);
      } catch (e) {
        if (!mounted) return;
        setConnected(false);
        setHealth(null);
        const code = (e as Error & { code?: string }).code;
        if (code === 'DISCONNECTED') {
          setError('Cannot reach the SEAM API');
        } else {
          setError((e as Error).message || String(e));
        }
      }
    }
    poll();
    const interval = setInterval(poll, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const Pane = PANES[activePane];

  return (
    <div id="root" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <ActivityBar active={activePane} onSelect={setActivePane} />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-deep)' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Pane />
          </div>
          <StatusBar connected={connected} health={health} error={error} />
        </main>
      </div>
    </div>
  );
}
