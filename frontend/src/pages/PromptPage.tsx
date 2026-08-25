import { useEffect, useState } from "react";
import { getHealth, sendPrompt, type LLMResponse } from "../services/api";

const MODEL_HINTS = ["7b", "3b"];

export default function PromptPage() {
  const [prompt, setPrompt] = useState("");
  const [modelHint, setModelHint] = useState("7b");
  const [maxTokens, setMaxTokens] = useState(256);
  const [useRag, setUseRag] = useState(false);
  const [response, setResponse] = useState<LLMResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backend, setBackend] = useState<string>("?");

  useEffect(() => {
    getHealth()
      .then((h) => setBackend(h.llm_backend))
      .catch(() => setBackend("unreachable"));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await sendPrompt({
        prompt,
        model_hint: modelHint,
        max_tokens: maxTokens,
        use_rag: useRag,
      });
      setResponse(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Neznáma chyba");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-slate-900 text-white px-6 py-4">
        <h1 className="text-xl font-semibold">Super magnet na klientov</h1>
        <p className="text-sm text-slate-300">
          Lokálny LLM Orchestrator · backend:{" "}
          <span className="font-mono text-emerald-400">{backend}</span>
        </p>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-4 bg-white p-5 rounded-xl shadow">
          <label className="block text-sm font-medium">Prompt</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={5}
            required
            placeholder="Zadajte príkaz pre lokálny model..."
            className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-500">Model</label>
              <select
                value={modelHint}
                onChange={(e) => setModelHint(e.target.value)}
                className="border rounded p-2 text-sm"
              >
                {MODEL_HINTS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500">Max tokenov</label>
              <input
                type="number"
                value={maxTokens}
                min={1}
                max={4096}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="border rounded p-2 text-sm w-28"
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
              />{" "}
              RAG
            </label>
            <button
              type="submit"
              disabled={loading}
              className="ml-auto bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {loading ? "Generujem..." : "Odoslať"}
            </button>
          </div>
        </form>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>
        )}

        {response && (
          <section className="bg-white p-5 rounded-xl shadow space-y-2">
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span className="px-2 py-0.5 bg-slate-100 rounded">{response.backend}</span>
              <span>{response.model}</span>
              {response.cached && (
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded">cache</span>
              )}
              {response.tokens_used != null && <span>· {response.tokens_used} tokenov</span>}
            </div>
            <pre className="whitespace-pre-wrap text-sm leading-relaxed">{response.text}</pre>
          </section>
        )}
      </main>
    </div>
  );
}
