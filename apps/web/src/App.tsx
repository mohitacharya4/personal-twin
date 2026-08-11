import { useEffect, useRef } from 'react';

import { ChatMessage } from './components/ChatMessage';
import { Composer } from './components/Composer';
import { Hero } from './components/Hero';
import { TwinHeader } from './components/TwinHeader';
import { useChatStream } from './lib/useChatStream';
import { useHealth } from './lib/useHealth';
import { useTheme } from './lib/useTheme';

export default function App() {
  const { theme, toggle } = useTheme();
  const health = useHealth();
  const { messages, isStreaming, send, stop } = useChatStream();

  const bottomRef = useRef<HTMLDivElement>(null);
  const lastText = messages.at(-1)?.text ?? '';
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, lastText]);

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      <TwinHeader health={health} theme={theme} onToggleTheme={toggle} />

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4">
          {empty ? (
            <Hero onPick={send} disabled={isStreaming} />
          ) : (
            <div className="space-y-6 py-6">
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
            </div>
          )}
          <div ref={bottomRef} className="h-2" />
        </div>
      </main>

      <footer className="border-t border-border/60 bg-bg/70 backdrop-blur-md">
        <div className="mx-auto max-w-3xl px-4 py-3">
          <Composer onSend={send} onStop={stop} isStreaming={isStreaming} />
        </div>
      </footer>
    </div>
  );
}
