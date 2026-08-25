import { useState } from "react";
import { login, register, type AuthResponse } from "../services/api";

export default function AuthForm({ onAuth }: { onAuth: (t: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res: AuthResponse =
        mode === "login"
          ? await login(username, password)
          : await register(username, password, "user");
      onAuth(res.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Neznáma chyba");
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex gap-2 text-sm">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={mode === "login" ? "text-blue-600 font-medium" : "text-slate-500"}
        >
          Prihlásiť
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={mode === "register" ? "text-blue-600 font-medium" : "text-slate-500"}
        >
          Registrovať
        </button>
      </div>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Používateľské meno"
        required
        minLength={3}
        className="w-full border rounded p-2 text-sm"
      />
      <input
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        type="password"
        placeholder="Heslo (min. 8 znakov)"
        required
        minLength={8}
        className="w-full border rounded p-2 text-sm"
      />
      {error && <div className="text-red-600 text-sm">{error}</div>}
      <button
        type="submit"
        className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium"
      >
        {mode === "login" ? "Prihlásiť" : "Registrovať"}
      </button>
    </form>
  );
}
