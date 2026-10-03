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

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role?: string;
}

export interface Lead {
  id: number;
  company_name: string;
  ico?: string | null;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  sector?: string | null;
  company_size?: string | null;
  source: string;
  score?: number | null;
  enriched: number;
  notes?: string | null;
}

function authHeader(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

function fail(res: Response, body: any): Error {
  const detail = body && (body.detail ?? body.error);
  return new Error(typeof detail === "string" ? detail : `HTTP ${res.status}`);
}

// ---- LLM ----
export async function sendPrompt(req: LLMRequest): Promise<LLMResponse> {
  const res = await fetch(`${API_BASE}/api/llm/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw fail(res, err);
  }
  return res.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Auth ----
// `role` is not sent: the backend assigns admin only to the first account on a
// fresh install and ignores any client-supplied role.
export async function register(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw fail(res, err);
  }
  return res.json();
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw fail(res, err);
  }
  return res.json();
}

// ---- Leads ----
export async function listLeads(token: string): Promise<Lead[]> {
  const res = await fetch(`${API_BASE}/api/leads`, { headers: authHeader(token) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function createLead(data: Partial<Lead>, token: string): Promise<Lead> {
  const res = await fetch(`${API_BASE}/api/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw fail(res, err);
  }
  return res.json();
}

export async function scoreLead(id: number, token: string): Promise<{ lead_id: number; score: number }> {
  const res = await fetch(`${API_BASE}/api/leads/${id}/score`, {
    method: "POST",
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteLead(id: number, token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/leads/${id}`, {
    method: "DELETE",
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function importCsv(file: File, token: string): Promise<any> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/leads/import`, {
    method: "POST",
    headers: authHeader(token),
    body: form,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Email ----
export interface EmailStatus {
  configured: boolean;
  mode: string;
}
export async function getEmailStatus(): Promise<EmailStatus> {
  const res = await fetch(`${API_BASE}/api/email/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function sendEmail(
  data: { to: string; subject: string; body: string },
  token: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/email/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Sequences ----
export interface SequenceStep {
  delay_hours: number;
  subject: string;
  body: string;
}
export interface Sequence {
  id: number;
  name: string;
  steps: SequenceStep[];
  ab_enabled?: boolean;
}
export async function listSequences(token: string): Promise<Sequence[]> {
  const res = await fetch(`${API_BASE}/api/sequences`, { headers: authHeader(token) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function createSequence(
  name: string,
  steps: SequenceStep[],
  token: string,
  abEnabled?: boolean,
  variants?: any
): Promise<Sequence> {
  const body: any = { name, steps };
  if (abEnabled) {
    body.ab_enabled = true;
    body.variants = variants;
  }
  const res = await fetch(`${API_BASE}/api/sequences`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function enrollSequence(id: number, leadIds: number[], token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/sequences/${id}/enroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ lead_ids: leadIds }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function runSequence(id: number, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/sequences/${id}/run`, {
    method: "POST",
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function abReportSequence(id: number, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/sequences/${id}/ab-report`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Export ----
export async function exportLeadsCsv(token: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export/leads.csv`, { headers: authHeader(token) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}
export async function exportSheets(spreadsheetId: string, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/export/google-sheets`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ spreadsheet_id: spreadsheetId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function exportDocs(title: string, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/export/google-docs`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Workflows ----
export interface Workflow {
  id: number;
  name: string;
  definition: { steps: any[] };
}
export async function listWorkflows(token: string): Promise<Workflow[]> {
  const res = await fetch(`${API_BASE}/api/workflows`, { headers: authHeader(token) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function createWorkflow(
  name: string,
  definition: { steps: any[] },
  token: string
): Promise<Workflow> {
  const res = await fetch(`${API_BASE}/api/workflows`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ name, definition }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function executeWorkflow(
  workflowId: number,
  leadId: number,
  token: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/workflows/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ workflow_id: workflowId, lead_id: leadId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Email deliverability ----
export async function checkDeliverability(domain: string, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/email/deliverability`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ domain }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Transcription ----
export async function transcriptionInsights(transcript: string, token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/transcription/insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify({ transcript }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
export async function transcribeFile(file: File, token: string): Promise<any> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/transcription/transcribe`, {
    method: "POST",
    headers: authHeader(token),
    body: form,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
