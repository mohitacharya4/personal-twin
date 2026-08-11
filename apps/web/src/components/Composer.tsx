import { useLayoutEffect, useRef, useState } from 'react';

import { persona } from '../persona';
import { SendIcon, StopIcon } from './icons';

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

const MAX_HEIGHT = 160;

export function Composer({ onSend, onStop, isStreaming }: Props) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (text === '' || isStreaming) return;
    onSend(text);
    setValue('');
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = value.trim() !== '' && !isStreaming;

  return (
    <div className="glass rounded-2xl p-2 shadow-xl">
      <div className="flex items-end gap-2">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder={`Ask ${persona.name} anything…`}
          className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-[15px] leading-relaxed text-ink placeholder:text-faint focus:outline-none"
          aria-label="Ask a question"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="focus-ring grid h-10 w-10 shrink-0 place-items-center rounded-xl border bg-surface/60 text-muted transition hover:text-ink"
            aria-label="Stop generating"
            title="Stop"
          >
            <StopIcon width={16} height={16} />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            className="btn-accent focus-ring h-10 w-10 shrink-0"
            aria-label="Send"
            title="Send"
          >
            <SendIcon width={18} height={18} />
          </button>
        )}
      </div>
      <p className="px-3 pb-1 pt-1 text-[11px] text-faint">
        Answers are grounded in indexed documents and cite their sources.{' '}
        <kbd className="rounded border border-border/70 px-1 font-sans text-[10px]">Enter</kbd> to
        send ·{' '}
        <kbd className="rounded border border-border/70 px-1 font-sans text-[10px]">
          Shift+Enter
        </kbd>{' '}
        for newline
      </p>
    </div>
  );
}
