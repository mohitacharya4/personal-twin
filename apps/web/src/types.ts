// Mirrors the backend SSE contract (apps/api/src/twin_api/streaming.py) and the
// Answer/Citation models (packages/rag/src/twin_rag/models.py).

export interface Citation {
  marker: number;
  chunk_id: string;
  title: string;
  source_id: string;
  uri: string | null;
}

export interface Context {
  marker: number;
  title: string;
  score: number;
  uri: string | null;
}

export interface TraceStep {
  node: string;
  detail: string | null;
}

export type ChatEvent =
  | { name: 'trace'; node: string; detail: string | null }
  | { name: 'token'; text: string }
  | { name: 'sources'; citations: Citation[]; contexts: Context[] }
  | { name: 'done'; answer: string; citations: Citation[] }
  | { name: 'error'; message: string };

export type MessageStatus = 'streaming' | 'done' | 'error';

export interface Message {
  id: string;
  role: 'user' | 'twin';
  text: string;
  trace: TraceStep[];
  citations: Citation[];
  contexts: Context[];
  status: MessageStatus;
  error: string | null;
}
