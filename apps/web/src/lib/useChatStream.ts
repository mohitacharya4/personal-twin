import { useCallback, useRef, useState } from 'react';

import type { Message } from '../types';
import { API_BASE } from './api';
import { readEvents } from './sse';

let counter = 0;
const nextId = () => `m${Date.now()}-${counter++}`;

function emptyTwin(): Message {
  return {
    id: nextId(),
    role: 'twin',
    text: '',
    trace: [],
    citations: [],
    contexts: [],
    status: 'streaming',
    error: null,
  };
}

/**
 * Owns the conversation and drives one /chat run at a time: appends tokens as they
 * arrive, records the live trace, and attaches sources on completion. Reducer-free —
 * it patches the single in-flight twin message by id.
 */
export function useChatStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const patch = useCallback((id: string, update: (m: Message) => Message) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? update(m) : m)));
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

  const send = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (trimmed === '' || isStreaming) return;

      const user: Message = {
        id: nextId(),
        role: 'user',
        text: trimmed,
        trace: [],
        citations: [],
        contexts: [],
        status: 'done',
        error: null,
      };
      const twin = emptyTwin();
      setMessages((prev) => [...prev, user, twin]);
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: trimmed }),
          signal: controller.signal,
        });
        if (!res.ok || res.body === null) throw new Error(`Request failed (${res.status})`);

        for await (const event of readEvents(res.body)) {
          switch (event.name) {
            case 'trace':
              patch(twin.id, (m) => ({
                ...m,
                trace: [...m.trace, { node: event.node, detail: event.detail }],
              }));
              break;
            case 'token':
              patch(twin.id, (m) => ({ ...m, text: m.text + event.text }));
              break;
            case 'sources':
              patch(twin.id, (m) => ({
                ...m,
                citations: event.citations,
                contexts: event.contexts,
              }));
              break;
            case 'done':
              patch(twin.id, (m) => ({
                ...m,
                status: 'done',
                text: event.answer || m.text,
                citations: event.citations.length ? event.citations : m.citations,
              }));
              break;
            case 'error':
              patch(twin.id, (m) => ({ ...m, status: 'error', error: event.message }));
              break;
          }
        }
        patch(twin.id, (m) => (m.status === 'streaming' ? { ...m, status: 'done' } : m));
      } catch (cause) {
        if (controller.signal.aborted) {
          patch(twin.id, (m) => ({ ...m, status: 'done' }));
        } else {
          const message = cause instanceof Error ? cause.message : 'The request failed.';
          patch(twin.id, (m) => ({ ...m, status: 'error', error: message }));
        }
      } finally {
        abortRef.current = null;
        setStreaming(false);
      }
    },
    [isStreaming, patch],
  );

  return { messages, isStreaming, send, stop };
}
