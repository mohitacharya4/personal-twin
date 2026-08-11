// SSE parsing for the /chat stream. Pure functions + one async generator, so the
// wire protocol is testable and independent of React. Unrecognised events are dropped
// rather than throwing — a malformed or future event type must not tear down a stream.

import type { ChatEvent, Citation, Context } from '../types';

/** Split a raw SSE buffer into complete event blocks plus the unconsumed remainder. */
export function splitEvents(buffer: string): { blocks: string[]; rest: string } {
  const parts = buffer.split('\n\n');
  const rest = parts.pop() ?? '';
  return { blocks: parts.filter((block) => block.trim() !== ''), rest };
}

/** Parse one `event:`/`data:` block into a typed event, or null if unrecognised. */
export function parseEvent(block: string): ChatEvent | null {
  let name = '';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) name = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (name === '' || dataLines.length === 0) return null;

  let payload: unknown;
  try {
    payload = JSON.parse(dataLines.join('\n'));
  } catch {
    return null;
  }
  if (typeof payload !== 'object' || payload === null) return null;
  const d = payload as Record<string, unknown>;

  switch (name) {
    case 'trace':
      return typeof d.node === 'string'
        ? { name, node: d.node, detail: typeof d.detail === 'string' ? d.detail : null }
        : null;
    case 'token':
      return typeof d.text === 'string' ? { name, text: d.text } : null;
    case 'sources':
      return {
        name,
        citations: Array.isArray(d.citations) ? (d.citations as Citation[]) : [],
        contexts: Array.isArray(d.contexts) ? (d.contexts as Context[]) : [],
      };
    case 'done':
      return typeof d.answer === 'string'
        ? {
            name,
            answer: d.answer,
            citations: Array.isArray(d.citations) ? (d.citations as Citation[]) : [],
          }
        : null;
    case 'error':
      return typeof d.message === 'string' ? { name, message: d.message } : null;
    default:
      return null;
  }
}

/** Decode a fetch response body stream into typed chat events as they arrive. */
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { blocks, rest } = splitEvents(buffer);
      buffer = rest;
      for (const block of blocks) {
        const event = parseEvent(block);
        if (event) yield event;
      }
    }
    const tail = parseEvent(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}
