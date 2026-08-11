import type { Citation, Context } from '../types';
import { ChevronIcon, DocIcon } from './icons';

interface Props {
  contexts: Context[];
  citations: Citation[];
  open: boolean;
  activeMarker: number | null;
  onToggle: () => void;
}

/** Collapsible evidence panel: the chunks retrieval surfaced, with similarity scores. */
export function SourcesPanel({ contexts, citations, open, activeMarker, onToggle }: Props) {
  if (contexts.length === 0) return null;
  const citedMarkers = new Set(citations.map((c) => c.marker));

  return (
    <div className="mt-3 border-t border-border/60 pt-2.5">
      <button
        type="button"
        onClick={onToggle}
        className="focus-ring flex items-center gap-1.5 rounded-md text-xs font-medium text-muted transition hover:text-ink"
        aria-expanded={open}
      >
        <DocIcon width={14} height={14} />
        {contexts.length} source{contexts.length === 1 ? '' : 's'}
        <ChevronIcon
          width={14}
          height={14}
          className={`transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <ul className="animate-fade-up mt-2.5 space-y-1.5">
          {contexts.map((ctx) => {
            const isActive = ctx.marker === activeMarker;
            const isCited = citedMarkers.has(ctx.marker);
            return (
              <li
                key={ctx.marker}
                className={[
                  'rounded-xl border px-3 py-2 transition-colors',
                  isActive ? 'border-violet/60 bg-violet/10' : 'border-border/60 bg-surface/40',
                ].join(' ')}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={[
                      'grid h-5 w-5 shrink-0 place-items-center rounded-md text-[11px] font-semibold',
                      isCited ? 'accent-gradient text-white' : 'bg-elevated text-muted',
                    ].join(' ')}
                  >
                    {ctx.marker}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{ctx.title}</span>
                  <span className="shrink-0 font-mono text-[11px] text-faint">
                    {ctx.score.toFixed(3)}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-2 pl-7">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-border/60">
                    <div
                      className="accent-gradient h-full rounded-full"
                      style={{ width: `${Math.max(0, Math.min(1, ctx.score)) * 100}%` }}
                    />
                  </div>
                  {ctx.uri && (
                    <span className="shrink-0 truncate font-mono text-[11px] text-faint">
                      {ctx.uri}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
