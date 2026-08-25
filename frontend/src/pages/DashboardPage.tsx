import { useEffect, useState } from "react";
import { listLeads, type Lead } from "../services/api";

function Card({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

export default function DashboardPage({ token }: { token: string }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  useEffect(() => {
    listLeads(token)
      .then(setLeads)
      .catch(() => setLeads([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const total = leads.length;
  const scored = leads.filter((l) => l.score != null);
  const avg = scored.length
    ? Math.round(scored.reduce((a, l) => a + (l.score || 0), 0) / scored.length)
    : 0;
  const enriched = leads.filter((l) => l.enriched === 1).length;
  const recent = leads.slice(0, 5);

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-6">
      <h2 className="text-lg font-semibold">Prehľad</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card label="Leady celkom" value={total} />
        <Card label="Priemerné skóre" value={avg} />
        <Card label="Obohacené (ORSR)" value={enriched} />
        <Card label="Skórované" value={scored.length} />
      </div>
      <section className="bg-white rounded-xl shadow p-4">
        <h3 className="font-medium mb-2">Nedávno pridané</h3>
        <ul className="text-sm divide-y">
          {recent.map((l) => (
            <li key={l.id} className="py-2 flex justify-between">
              <span>{l.company_name}</span>
              <span className="text-slate-500">{l.score != null ? l.score : "—"}</span>
            </li>
          ))}
          {recent.length === 0 && (
            <li className="py-2 text-slate-400">Zatiaľ žiadne leady.</li>
          )}
        </ul>
      </section>
    </main>
  );
}
