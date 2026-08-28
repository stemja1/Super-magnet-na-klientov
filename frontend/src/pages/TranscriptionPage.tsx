import { useState } from "react";
import { transcriptionInsights, transcribeFile } from "../services/api";

export default function TranscriptionPage({ token }: { token: string }) {
  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function getInsights() {
    setError(null);
    try {
      const r = await transcriptionInsights(transcript, token);
      setSummary(r.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba");
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setError(null);
    try {
      const r = await transcribeFile(f, token);
      setTranscript(r.text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba");
    }
    e.target.value = "";
  }

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <section className="bg-white p-5 rounded-xl shadow space-y-3">
        <h2 className="font-semibold">Transkripcia & call insights</h2>
        <label className="text-sm text-slate-600">
          Nahrať audio (whisper.cpp, inak sandbox):{" "}
          <input type="file" accept="audio/*" onChange={onFile} className="text-sm" />
        </label>
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          rows={6}
          placeholder="Prepis hovoru..."
          className="w-full border rounded p-2 text-sm"
        />
        <button
          onClick={getInsights}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          Získaj insights
        </button>
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </section>

      {summary && (
        <section className="bg-white rounded-xl shadow p-4">
          <h3 className="font-medium mb-2">Zhrnutie</h3>
          <pre className="whitespace-pre-wrap text-sm">{summary}</pre>
        </section>
      )}
    </main>
  );
}
