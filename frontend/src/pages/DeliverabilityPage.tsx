import { useState } from "react";
import { checkDeliverability } from "../services/api";

export default function DeliverabilityPage({ token }: { token: string }) {
  const [domain, setDomain] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setResult(await checkDeliverability(domain, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba");
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <form onSubmit={check} className="bg-white p-5 rounded-xl shadow space-y-3">
        <h2 className="font-semibold">Email deliverability (SPF / DKIM / DMARC)</h2>
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          placeholder="doména (napr. firma.sk)"
          required
          className="w-full border rounded p-2 text-sm"
        />
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">
          Skontrolovať
        </button>
      </form>

      {error && <div className="text-red-600 text-sm">{error}</div>}

      {result && (
        <section className="bg-white rounded-xl shadow p-4 space-y-2 text-sm">
          <div className="flex items-center gap-3">
            <span className="font-medium">Skóre:</span>
            <span className="text-lg font-semibold">{result.score}/100</span>
            <span className="text-slate-500">({result.mode})</span>
          </div>
          <ul className="space-y-1">
            <li>SPF: {result.spf ? "✅" : "❌"}</li>
            <li>DMARC: {result.dmarc ? "✅" : "❌"}</li>
            <li>DKIM nájdený: {result.dkim_found ? "✅" : "❌"}</li>
          </ul>
          {result.issues.length > 0 && (
            <div className="text-red-600">
              <b>Problémy:</b>
              <ul className="list-disc ml-5">
                {result.issues.map((i: string, idx: number) => (
                  <li key={idx}>{i}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
