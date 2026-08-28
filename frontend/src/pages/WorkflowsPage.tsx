import { useEffect, useState } from "react";
import {
  createWorkflow,
  executeWorkflow,
  listWorkflows,
  type Workflow,
} from "../services/api";

interface WFStep {
  type: string;
  subject?: string;
  body?: string;
  hours?: number;
  message?: string;
  field?: string;
  op?: string;
  value?: string;
}

const STEP_TYPES = ["score", "send_email", "enrich", "log", "wait", "condition"];

export default function WorkflowsPage({ token }: { token: string }) {
  const [name, setName] = useState("");
  const [steps, setSteps] = useState<WFStep[]>([{ type: "score" }]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [leadId, setLeadId] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    try {
      setWorkflows(await listWorkflows(token));
    } catch {
      setWorkflows([]);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function addStep() {
    setSteps([...steps, { type: "score" }]);
  }
  function updateStep(i: number, patch: Partial<WFStep>) {
    setSteps(steps.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  }
  function removeStep(i: number) {
    setSteps(steps.filter((_, idx) => idx !== i));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await createWorkflow(name, { steps }, token);
      setName("");
      setSteps([{ type: "score" }]);
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Chyba");
    }
  }

  async function run(wfId: number) {
    const id = parseInt(leadId.trim(), 10);
    if (!id) {
      setMsg("Zadaj lead id pre spustenie");
      return;
    }
    try {
      const r = await executeWorkflow(wfId, id, token);
      setMsg(JSON.stringify(r.steps));
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Chyba");
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <form onSubmit={save} className="bg-white p-5 rounded-xl shadow space-y-3">
        <h2 className="font-semibold">Nový workflow</h2>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Názov workflowu"
          required
          className="w-full border rounded p-2 text-sm"
        />
        {steps.map((s, i) => (
          <div key={i} className="border rounded p-2 space-y-2">
            <div className="flex items-center gap-2">
              <select
                value={s.type}
                onChange={(e) => updateStep(i, { type: e.target.value })}
                className="border rounded p-1 text-sm"
              >
                {STEP_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeStep(i)}
                className="text-red-600 text-xs"
              >
                Odstrániť
              </button>
            </div>
            {s.type === "send_email" && (
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={s.subject || ""}
                  onChange={(e) => updateStep(i, { subject: e.target.value })}
                  placeholder="Predmet"
                  className="border rounded p-1 text-sm"
                />
                <input
                  value={s.body || ""}
                  onChange={(e) => updateStep(i, { body: e.target.value })}
                  placeholder="Telo"
                  className="border rounded p-1 text-sm"
                />
              </div>
            )}
            {s.type === "wait" && (
              <input
                type="number"
                value={s.hours ?? 24}
                onChange={(e) => updateStep(i, { hours: Number(e.target.value) })}
                placeholder="Oneskorenie (hod)"
                className="border rounded p-1 text-sm w-40"
              />
            )}
            {s.type === "log" && (
              <input
                value={s.message || ""}
                onChange={(e) => updateStep(i, { message: e.target.value })}
                placeholder="Správa"
                className="border rounded p-1 text-sm w-full"
              />
            )}
            {s.type === "condition" && (
              <div className="flex gap-2">
                <input
                  value={s.field || ""}
                  onChange={(e) => updateStep(i, { field: e.target.value })}
                  placeholder="pole (napr. sector)"
                  className="border rounded p-1 text-sm"
                />
                <input
                  value={s.op || "=="}
                  onChange={(e) => updateStep(i, { op: e.target.value })}
                  placeholder="op"
                  className="border rounded p-1 text-sm w-16"
                />
                <input
                  value={s.value || ""}
                  onChange={(e) => updateStep(i, { value: e.target.value })}
                  placeholder="hodnota"
                  className="border rounded p-1 text-sm"
                />
              </div>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={addStep}
            className="text-blue-600 text-sm hover:underline"
          >
            + Krok
          </button>
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">
            Uložiť workflow
          </button>
        </div>
      </form>

      {msg && <div className="text-sm bg-slate-100 p-2 rounded">{msg}</div>}

      <section className="bg-white rounded-xl shadow p-4 space-y-2">
        <h3 className="font-medium">Workflowy</h3>
        <div className="flex items-center gap-2 mb-2">
          <input
            value={leadId}
            onChange={(e) => setLeadId(e.target.value)}
            placeholder="lead id na spustenie"
            className="border rounded p-1 text-sm w-40"
          />
        </div>
        {workflows.map((w) => (
          <div key={w.id} className="border-t pt-2 text-sm flex justify-between">
            <div>
              <b>{w.name}</b> · {w.definition.steps.length} krokov
            </div>
            <button
              onClick={() => run(w.id)}
              className="text-emerald-600 hover:underline text-xs"
            >
              Spustiť
            </button>
          </div>
        ))}
        {workflows.length === 0 && (
          <div className="text-slate-400">Zatiaľ žiadne workflowy.</div>
        )}
      </section>
    </main>
  );
}
