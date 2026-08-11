import { useEffect, useState } from 'react';

import { API_BASE, type Health } from './api';

export type HealthState =
  { status: 'loading' } | { status: 'up'; health: Health } | { status: 'down' };

/** Poll /health so the header can show a live connection + document-count indicator. */
export function useHealth(intervalMs = 15000): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' });

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) throw new Error();
        const health = (await res.json()) as Health;
        if (active) setState({ status: 'up', health });
      } catch {
        if (active) setState({ status: 'down' });
      }
    };
    void check();
    const timer = setInterval(check, intervalMs);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [intervalMs]);

  return state;
}
