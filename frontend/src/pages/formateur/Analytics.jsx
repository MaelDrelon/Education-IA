import { useState } from "react";
import { api } from "../../api";

const SUGGESTIONS = [
  "Quel exercice a le plus faible taux de réussite ?",
  "Quels apprenants n'ont pas terminé l'examen de la semaine dernière ?",
  "Sur quelle notion la classe bloque-t-elle le plus ?",
];

export default function Analytics() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);

  const ask = async (q) => {
    if (!q.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setBusy(true);
    try {
      const res = await api("/ai/analyze", { method: "POST", body: { question: q } });
      setMessages((m) => [...m, { role: "bot", text: res.answer, trace: res.trace }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: `Erreur : ${e.message}` }]);
    } finally { setBusy(false); }
  };

  return (
    <>
      <h1>Analyse des résultats</h1>
      <p className="muted">L'assistant interroge la base via des requêtes prédéfinies, limitées à vos cours.
        Le détail des données utilisées est consultable sous chaque réponse.</p>

      <div className="row" style={{ margin: "12px 0" }}>
        {SUGGESTIONS.map((s) => <button key={s} className="ghost" onClick={() => ask(s)} disabled={busy}>{s}</button>)}
      </div>

      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
            {m.trace?.length > 0 && (
              <details>
                <summary>Données utilisées ({m.trace.length} requête{m.trace.length > 1 ? "s" : ""})</summary>
                {m.trace.map((t, j) => (
                  <div key={j}>
                    <p className="muted"><code>{t.name}({JSON.stringify(t.input)})</code></p>
                    <TraceTable rows={t.result} />
                  </div>
                ))}
              </details>
            )}
          </div>
        ))}
        {busy && <div className="msg bot muted">Analyse en cours…</div>}
      </div>

      <form className="row" style={{ marginTop: 16 }} onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <input className="grow" placeholder="Posez une question sur les résultats…" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button disabled={busy}>Envoyer</button>
      </form>
    </>
  );
}

function TraceTable({ rows }) {
  if (!Array.isArray(rows)) return <pre>{JSON.stringify(rows, null, 2)}</pre>;
  if (!rows.length) return <p className="muted">Aucune ligne.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <table>
      <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{String(r[c])}</td>)}</tr>)}</tbody>
    </table>
  );
}
