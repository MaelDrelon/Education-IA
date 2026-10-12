import { useState } from "react";

const EMPTY = { title: "", statement: "", type: "qcm", choices: ["", ""], solution: "", difficulty: "debutant", notion: "" };

/** Formulaire de création / édition d'un exercice. */
export default function ExerciseForm({ initial, onSubmit, onCancel, submitLabel = "Enregistrer" }) {
  const [f, setF] = useState(() => ({ ...EMPTY, ...initial, choices: initial?.choices || EMPTY.choices }));
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const body = { ...f, choices: f.type === "qcm" ? f.choices.map((c) => c.trim()).filter(Boolean) : null };
    try { await onSubmit(body); } catch (err) { setError(err.message); }
  };

  const setChoice = (i, v) => setF({ ...f, choices: f.choices.map((c, j) => (j === i ? v : c)) });

  return (
    <form className="stack" onSubmit={submit}>
      <div className="row">
        <label className="grow">Titre<input value={f.title} onChange={set("title")} required /></label>
        <label>Type
          <select value={f.type} onChange={set("type")}>
            <option value="qcm">QCM</option><option value="code">Code</option><option value="texte">Texte libre</option>
          </select>
        </label>
        <label>Niveau
          <select value={f.difficulty} onChange={set("difficulty")}>
            <option value="debutant">Débutant</option><option value="intermediaire">Intermédiaire</option><option value="avance">Avancé</option>
          </select>
        </label>
        <label>Notion<input value={f.notion} onChange={set("notion")} placeholder="ex. boucle for" required /></label>
      </div>
      <label>Énoncé (Markdown)<textarea value={f.statement} onChange={set("statement")} required /></label>

      {f.type === "qcm" ? (
        <fieldset className="stack" style={{ border: "none", padding: 0 }}>
          <span className="muted">Choix — cochez la bonne réponse</span>
          {f.choices.map((c, i) => (
            <div className="row" key={i}>
              <input type="radio" style={{ width: "auto" }} name="solution" checked={c !== "" && f.solution === c}
                     onChange={() => setF({ ...f, solution: c })} />
              <input className="grow" value={c} onChange={(e) => setChoice(i, e.target.value)} />
            </div>
          ))}
          <button type="button" className="ghost" onClick={() => setF({ ...f, choices: [...f.choices, ""] })}>+ Choix</button>
        </fieldset>
      ) : (
        <label>Corrigé<textarea className={f.type === "code" ? "code" : ""} value={f.solution} onChange={set("solution")} required /></label>
      )}

      {error && <p className="error">{error}</p>}
      <div className="row">
        <button>{submitLabel}</button>
        {onCancel && <button type="button" className="ghost" onClick={onCancel}>Annuler</button>}
      </div>
    </form>
  );
}
