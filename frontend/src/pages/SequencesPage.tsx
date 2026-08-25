import { useEffect, useState } from "react";
import {
  createSequence,
  enrollSequence,
  listSequences,
  runSequence,
  type Sequence,
  type SequenceStep,
} from "../services/api";

export default function SequencesPage({ token }: { token: string }) {
  const [seqs, setSeqs] = useState<Sequence[]>([]);
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [delay, setDelay] = useState(24);
  const [enrollId, setEnrollId] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    try {
      setSeqs(await listSequences(token));
    } catch {
      setSeqs([]);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    const steps: SequenceStep[] = [{ delay_hours: delay, subject, body }];
    try {
      await createSequence(name, steps, token);
      setName("");
      setSubject("");
      setBody("");
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Chyba");
    }
  }

  async function enroll(sid: number) {
    const ids = enrollId
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n));
    try {
      const r = await enrollSequence(sid, ids, token);
      setMsg(JSON.stringify(r));
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Chyba");
    }
  }

  async function run(sid: number) {
    try {
      const r = await runSequence(sid, token);
      setMsg(JSON.stringify(r));
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Chyba");
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <form onSubmit={create} className="bg-white p-5 rounded-xl shadow space-y-3">
        <h2 className="font-semibold">Nová sekvencia</h2>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Názov"
          required
          className="w-full border rounded p-2 text-sm"
        />
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Predmet (použi {contact_name})"
          className="w-full border rounded p-2 text-sm"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Telo emailu ({company_name})"
          rows={3}
          className="w-full border rounded p-2 text-sm"
        />
        <input
          type="number"
          value={delay}
          onChange={(e) => setDelay(Number(e.target.value))}
          placeholder="Oneskorenie (hod)"
          className="w-48 border rounded p-2 text-sm"
        />
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">
          Vytvoriť
        </button>
      </form>

      {msg && <div className="text-sm bg-slate-100 p-2 rounded">{msg}</div>}

      <section className="bg-white rounded-xl shadow p-4 space-y-2">
        <h3 className="font-medium">Sekvencie</h3>
        {seqs.map((s) => (
          <div
            key={s.id}
            className="border-t pt-2 text-sm flex items-center justify-between gap-2"
          >
            <div>
              <b>{s.name}</b> · {s.steps.length} krokov
            </div>
            <div className="flex gap-2 items-center">
              <input
                value={enrollId}
                onChange={(e) => setEnrollId(e.target.value)}
                placeholder="lead id(s)"
                className="border rounded p-1 text-xs w-28"
              />
              <button onClick={() => enroll(s.id)} className="text-blue-600 hover:underline text-xs">
                Zapísať
              </button>
              <button onClick={() => run(s.id)} className="text-emerald-600 hover:underline text-xs">
                Spustiť
              </button>
            </div>
          </div>
        ))}
        {seqs.length === 0 && <div className="text-slate-400">Zatiaľ žiadne sekvencie.</div>}
      </section>
    </main>
  );
}
