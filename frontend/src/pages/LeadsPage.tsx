import { useEffect, useState } from "react";
import {
  createLead,
  deleteLead,
  importCsv,
  listLeads,
  scoreLead,
  type Lead,
} from "../services/api";

export default function LeadsPage({ token }: { token: string }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [form, setForm] = useState({
    company_name: "",
    ico: "",
    email: "",
    sector: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLeads(await listLeads(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba načítania");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createLead(
        { company_name: form.company_name, ico: form.ico || undefined, email: form.email || undefined, sector: form.sector || undefined },
        token
      );
      setForm({ company_name: "", ico: "", email: "", sector: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba vytvorenia");
    }
  }

  async function score(id: number) {
    try {
      const r = await scoreLead(id, token);
      setLeads((ls) => ls.map((l) => (l.id === id ? { ...l, score: r.score } : l)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba skórovania");
    }
  }

  async function del(id: number) {
    await deleteLead(id, token);
    await load();
  }

  async function onImport(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      await importCsv(f, token);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chyba importu");
    }
    e.target.value = "";
  }

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-6">
      <form onSubmit={submit} className="bg-white p-5 rounded-xl shadow space-y-3">
        <h2 className="font-semibold">Nový lead</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <input
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            placeholder="Názov firmy *"
            required
            className="border rounded p-2 text-sm"
          />
          <input
            value={form.ico}
            onChange={(e) => setForm({ ...form, ico: e.target.value })}
            placeholder="IČO"
            className="border rounded p-2 text-sm"
          />
          <input
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Email"
            className="border rounded p-2 text-sm"
          />
          <input
            value={form.sector}
            onChange={(e) => setForm({ ...form, sector: e.target.value })}
            placeholder="Odvetvie"
            className="border rounded p-2 text-sm"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            Pridať
          </button>
          <label className="text-sm text-slate-600">
            Import CSV:{" "}
            <input type="file" accept=".csv" onChange={onImport} className="text-sm" />
          </label>
        </div>
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </form>

      <section className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-3">Názov</th>
              <th className="p-3">IČO</th>
              <th className="p-3">Odvetvie</th>
              <th className="p-3">Skóre</th>
              <th className="p-3">Akcie</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id} className="border-t">
                <td className="p-3">{l.company_name}</td>
                <td className="p-3">{l.ico ?? "—"}</td>
                <td className="p-3">{l.sector ?? "—"}</td>
                <td className="p-3">{l.score != null ? l.score : "—"}</td>
                <td className="p-3 flex gap-2">
                  <button
                    onClick={() => score(l.id)}
                    className="text-blue-600 hover:underline"
                  >
                    Skóre
                  </button>
                  <button
                    onClick={() => del(l.id)}
                    className="text-red-600 hover:underline"
                  >
                    Zmazať
                  </button>
                </td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td colSpan={5} className="p-4 text-center text-slate-400">
                  Zatiaľ žiadne leady.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
