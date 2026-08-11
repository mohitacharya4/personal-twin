import { useState } from 'react';

import type { Message } from '../types';
import { AnswerBody } from './AnswerBody';
import { Avatar } from './Avatar';
import { SourcesPanel } from './SourcesPanel';
import { TraceTimeline } from './TraceTimeline';
import { AlertIcon } from './icons';

export function ChatMessage({ message }: { message: Message }) {
  if (message.role === 'user') return <UserMessage text={message.text} />;
  return <TwinMessage message={message} />;
}

function UserMessage({ text }: { text: string }) {
  return (
    <div className="animate-fade-up flex justify-end">
      <div className="accent-gradient max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-md">
        {text}
      </div>
    </div>
  );
}

function TwinMessage({ message }: { message: Message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [activeMarker, setActiveMarker] = useState<number | null>(null);

  const onCite = (marker: number) => {
    setSourcesOpen(true);
    setActiveMarker(marker);
  };

  const isEmpty = message.text === '' && message.status === 'streaming';

  return (
    <div className="animate-fade-up flex gap-3">
      <Avatar size={32} />
      <div className="card min-w-0 flex-1 px-4 py-3">
        <TraceTimeline trace={message.trace} status={message.status} />

        {message.status === 'error' ? (
          <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            <AlertIcon width={16} height={16} className="mt-0.5 shrink-0" />
            <span>{message.error ?? 'Something went wrong.'}</span>
          </div>
        ) : isEmpty && message.trace.length === 0 ? (
          <ThinkingDots />
        ) : (
          <AnswerBody
            text={message.text}
            citations={message.citations}
            streaming={message.status === 'streaming'}
            onCite={onCite}
          />
        )}

        <SourcesPanel
          contexts={message.contexts}
          citations={message.citations}
          open={sourcesOpen}
          activeMarker={activeMarker}
          onToggle={() => setSourcesOpen((v) => !v)}
        />
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 py-1" aria-label="Thinking">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-muted"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}
