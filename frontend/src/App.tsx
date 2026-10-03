import { useState } from "react";
import PromptPage from "./pages/PromptPage";
import LeadsPage from "./pages/LeadsPage";
import DashboardPage from "./pages/DashboardPage";
import SequencesPage from "./pages/SequencesPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import DeliverabilityPage from "./pages/DeliverabilityPage";
import TranscriptionPage from "./pages/TranscriptionPage";
import AuthForm from "./components/AuthForm";

type View =
  | "dashboard"
  | "leads"
  | "sequences"
  | "workflows"
  | "deliverability"
  | "transcription"
  | "prompt";

const NAV: View[] = [
  "dashboard",
  "leads",
  "sequences",
  "workflows",
  "deliverability",
  "transcription",
  "prompt",
];

// Token lives in sessionStorage, not localStorage: it is dropped when the window
// closes and is not readable by other origins' scripts that persist on disk.
// (A cookie with HttpOnly would be stronger still — see docs/roadmap.)
const TOKEN_KEY = "smk_token";

function readToken(): string {
  const stored = sessionStorage.getItem(TOKEN_KEY);
  if (!stored) return "";
  // Drop tokens left behind by older builds that used localStorage.
  localStorage.removeItem(TOKEN_KEY);
  return stored;
}

export default function App() {
  const [token, setToken] = useState<string>(readToken);
  const [view, setView] = useState<View>("dashboard");

  function handleAuth(t: string) {
    sessionStorage.setItem(TOKEN_KEY, t);
    setToken(t);
  }
  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken("");
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-full max-w-sm bg-white p-6 rounded-xl shadow">
          <h1 className="text-xl font-semibold mb-4">Super magnet na klientov</h1>
          <AuthForm onAuth={handleAuth} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-slate-900 text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="font-semibold">Super magnet na klientov</span>
          <nav className="flex gap-3 text-sm">
            {NAV.map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={view === v ? "text-emerald-400 capitalize" : "text-slate-300 capitalize"}
              >
                {v === "prompt" ? "LLM Prompt" : v}
              </button>
            ))}
          </nav>
        </div>
        <button onClick={logout} className="text-sm text-slate-300 hover:text-white">
          Odhlásiť
        </button>
      </header>
      <main>
        {view === "dashboard" && <DashboardPage token={token} />}
        {view === "leads" && <LeadsPage token={token} />}
        {view === "sequences" && <SequencesPage token={token} />}
        {view === "workflows" && <WorkflowsPage token={token} />}
        {view === "deliverability" && <DeliverabilityPage token={token} />}
        {view === "transcription" && <TranscriptionPage token={token} />}
        {view === "prompt" && <PromptPage />}
      </main>
    </div>
  );
}
