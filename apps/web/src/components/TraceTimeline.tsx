import type { MessageStatus, TraceStep } from '../types';
import { CheckIcon, PenIcon, SearchIcon } from './icons';

interface Props {
  trace: TraceStep[];
  status: MessageStatus;
}

const STEPS = [
  { node: 'retrieve', label: 'Retrieve', Icon: SearchIcon },
  { node: 'generate', label: 'Generate', Icon: PenIcon },
  { node: 'verify', label: 'Verify', Icon: CheckIcon },
] as const;

type StepState = 'done' | 'active' | 'idle';

/** A compact live view of the pipeline: retrieve → generate → verify. */
export function TraceTimeline({ trace, status }: Props) {
  if (trace.length === 0) return null;

  const seen = new Set(trace.map((t) => t.node));
  const lastCanonical = [...trace]
    .reverse()
    .find((t) => STEPS.some((s) => s.node === t.node))?.node;
  const streaming = status === 'streaming';

  const stateFor = (node: string): StepState => {
    if (!seen.has(node)) return 'idle';
    if (streaming && node === lastCanonical) return 'active';
    return 'done';
  };

  const latestDetail = [...trace].reverse().find((t) => t.detail)?.detail ?? null;

  return (
    <div className="mb-2.5 flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        {STEPS.map(({ node, label, Icon }, i) => {
          const state = stateFor(node);
          return (
            <div key={node} className="flex items-center gap-1.5">
              <span
                className={[
                  'inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-xs font-medium transition-all',
                  state === 'done' && 'border-violet/30 bg-violet/10 text-violet',
                  state === 'active' && 'border-violet/50 bg-violet/15 text-violet shadow-sm',
                  state === 'idle' && 'border-border/60 bg-surface/40 text-faint',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <Icon
                  width={13}
                  height={13}
                  className={state === 'active' ? 'animate-pulse-dot' : ''}
                />
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <span
                  className={
                    stateFor(STEPS[i + 1]!.node) !== 'idle'
                      ? 'h-px w-3 bg-violet/40'
                      : 'h-px w-3 bg-border'
                  }
                />
              )}
            </div>
          );
        })}
      </div>
      {streaming && latestDetail && (
        <div
          className="animate-shimmer bg-clip-text text-xs text-transparent"
          style={{
            backgroundImage:
              'linear-gradient(90deg, rgb(var(--faint)) 0%, rgb(var(--ink)) 50%, rgb(var(--faint)) 100%)',
            backgroundSize: '200% 100%',
          }}
        >
          {latestDetail}
        </div>
      )}
    </div>
  );
}
