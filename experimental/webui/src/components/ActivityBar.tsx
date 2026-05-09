import React from 'react';
import { icons } from './icons';

export type PaneId = 'status' | 'compile' | 'search' | 'context' | 'settings';

const paneOrder: PaneId[] = ['status', 'compile', 'search', 'context', 'settings'];
const paneLabels: Record<PaneId, React.ReactNode> = {
  status: icons.status,
  compile: icons.compile,
  search: icons.search,
  context: icons.context,
  settings: icons.settings,
};

interface ActivityBarProps {
  active: PaneId;
  onSelect: (id: PaneId) => void;
}

export default function ActivityBar({ active, onSelect }: ActivityBarProps) {
  return (
    <div
      style={{
        width: 48,
        background: '#020913',
        borderRight: '1px solid rgba(47,99,255,0.15)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: 8,
        gap: 6,
        flexShrink: 0,
      }}
    >
      {paneOrder.map((id) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            title={id}
            onClick={() => onSelect(id)}
            style={{
              width: 36,
              height: 36,
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: isActive ? 'rgba(127,224,255,0.1)' : 'transparent',
              border: isActive ? '1px solid rgba(127,224,255,0.3)' : '1px solid transparent',
              color: isActive ? '#7fe0ff' : '#5a7a9a',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {paneLabels[id]}
          </button>
        );
      })}
    </div>
  );
}
