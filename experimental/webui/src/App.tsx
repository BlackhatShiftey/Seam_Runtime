import React from 'react';
import './index.css';

const ORIGINAL_DASHBOARD_URL = '/seam-dashboard-prototype.html';

export default function App() {
  const [failed, setFailed] = React.useState(false);

  if (failed) {
    return (
      <main className="prototype-fallback">
        <h1>SEAM dashboard prototype is unavailable</h1>
        <p>
          Vite should be serving the preserved original from
          <code> experimental/webui/prototype-backup/</code>.
        </p>
      </main>
    );
  }

  return (
    <iframe
      className="prototype-frame"
      src={ORIGINAL_DASHBOARD_URL}
      title="SEAM original dashboard prototype"
      onError={() => setFailed(true)}
    />
  );
}
