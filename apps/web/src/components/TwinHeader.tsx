import type { HealthState } from '../lib/useHealth';
import type { Theme } from '../lib/useTheme';
import { persona } from '../persona';
import { Avatar } from './Avatar';
import { MoonIcon, SunIcon } from './icons';

interface Props {
  health: HealthState;
  theme: Theme;
  onToggleTheme: () => void;
}

function StatusDot({ health }: { health: HealthState }) {
  if (health.status === 'up') {
    const docs = health.health.vector_store.documents;
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
        </span>
        online
        {typeof docs === 'number' && <span className="text-faint">· {docs} chunks indexed</span>}
      </span>
    );
  }
  if (health.status === 'down') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted">
        <span className="h-2 w-2 rounded-full bg-rose-500" /> offline
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-faint">
      <span className="h-2 w-2 animate-pulse-dot rounded-full bg-faint" /> connecting…
    </span>
  );
}

export function TwinHeader({ health, theme, onToggleTheme }: Props) {
  return (
    <header className="glass sticky top-0 z-20 border-b">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <Avatar size={40} initials={persona.initials} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-[15px] font-semibold">
              <span className="gradient-text">{persona.name}</span>
              <span className="text-muted"> · Digital Twin</span>
            </h1>
          </div>
          <StatusDot health={health} />
        </div>
        <button
          type="button"
          onClick={onToggleTheme}
          className="focus-ring grid h-9 w-9 place-items-center rounded-xl border bg-surface/50 text-muted transition hover:text-ink"
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>
    </header>
  );
}
