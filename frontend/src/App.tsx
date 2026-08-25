import { useState } from "react";
import PromptPage from "./pages/PromptPage";
import LeadsPage from "./pages/LeadsPage";
import AuthForm from "./components/AuthForm";

export default function App() {
  const [token, setToken] = useState<string>(localStorage.getItem("smk_token") || "");
  const [view, setView] = useState<"prompt" | "leads">("prompt");

  function handleAuth(t: string) {
    localStorage.setItem("smk_token", t);
    setToken(t);
  }
  function logout() {
    localStorage.removeItem("smk_token");
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
        <div className="flex items-center gap-5">
          <span className="font-semibold">Super magnet na klientov</span>
          <nav className="flex gap-3 text-sm">
            <button
              onClick={() => setView("prompt")}
              className={view === "prompt" ? "text-emerald-400" : "text-slate-300"}
            >
              Prompt
            </button>
            <button
              onClick={() => setView("leads")}
              className={view === "leads" ? "text-emerald-400" : "text-slate-300"}
            >
              Leads
            </button>
          </nav>
        </div>
        <button onClick={logout} className="text-sm text-slate-300 hover:text-white">
          Odhlásiť
        </button>
      </header>
      <main>{view === "prompt" ? <PromptPage /> : <LeadsPage token={token} />}</main>
    </div>
  );
}
