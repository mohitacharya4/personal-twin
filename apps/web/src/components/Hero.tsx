import { persona } from '../persona';
import { Avatar } from './Avatar';
import { SparkleIcon } from './icons';

interface Props {
  onPick: (question: string) => void;
  disabled: boolean;
}

/** First-run welcome: who the twin is, and a few starter questions to break the ice. */
export function Hero({ onPick, disabled }: Props) {
  return (
    <div className="animate-fade-up flex flex-col items-center py-14 text-center">
      <Avatar size={72} initials={persona.initials} />
      <h2 className="mt-5 text-2xl font-semibold tracking-tight">{persona.fullName}</h2>
      <p className="mt-1 text-sm font-medium text-muted">{persona.role}</p>
      <p className="mt-4 max-w-md text-balance text-[15px] leading-relaxed text-muted">
        {persona.tagline}
      </p>

      <div className="mt-8 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-faint">
        <SparkleIcon width={14} height={14} />
        Try asking
      </div>
      <div className="mt-3 flex max-w-xl flex-wrap justify-center gap-2">
        {persona.starters.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onPick(q)}
            className="chip focus-ring disabled:pointer-events-none disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
