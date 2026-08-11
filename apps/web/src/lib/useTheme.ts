import { useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';

const KEY = 'twin-theme';

function initial(): Theme {
  const stored = localStorage.getItem(KEY);
  if (stored === 'dark' || stored === 'light') return stored;
  // Dark-first: the console aesthetic is the primary design; light is opt-in via the toggle.
  return 'dark';
}

/** Dark-first theme with a manual toggle, persisted to localStorage. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initial);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  return { theme, toggle };
}
