// Frontend API client for the Super magnet na klientov backend.
// In dev (Vite) it calls the FastAPI server directly; in the Tauri build the
// same relative/localhost URL is proxied by the WebView.

const API_BASE: string = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface LLMRequest {
  prompt: string;
  model_hint?: string;
  top_k?: number;
  max_tokens?: number;
  temperature?: number;
  use_rag?: boolean;
}

export interface LLMResponse {
  text: string;
  backend: string;
  model: string;
  model_hint?: string;
  tokens_used?: number;
  finish_reason?: string;
  cached?: boolean;
}

export interface HealthResponse {
  status: string;
  llm_backend: string;
  version: string;
}

export async function sendPrompt(req: LLMRequest): Promise<LLMResponse> {
  const res = await fetch(`${API_BASE}/api/llm/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
