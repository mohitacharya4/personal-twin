// API base. Empty by default so requests are same-origin and hit the Vite dev proxy
// (or the nginx proxy in the Docker image). Override with VITE_API_BASE when the API
// lives on another origin.
export const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export interface Health {
  status: string;
  env: string;
  tracing: boolean;
  vector_store: { backend: string; ok: boolean | null; documents: number | null };
}
