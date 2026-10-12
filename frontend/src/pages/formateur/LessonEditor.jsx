import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, LABELS } from "../../api";
import ExerciseForm from "../../components/ExerciseForm";

export default function LessonEditor() {
  const { id } = useParams();
  const [lesson, setLesson] = useState(null);
  const [exercises, setExercises] = useState([]);
  const [editing, setEditing] = useState(null); // id d'exercice, "new" ou null
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    setLesson(await api(`/lessons/${id}`));
    setExercises(await api(`/lessons/${id}/exercises`));
  };
  useEffect(() => { load().catch((e) => setError(e.message)); }, [id]);

  const saveLesson = async () => {
    await api(`/lessons/${id}`, { method: "PATCH", body: { title: lesson.title, content: lesson.content } });
    setSaved("Enregistré");
    setTimeout(() => setSaved(""), 1500);
  };

  const act = (fn) => async (...args) => {
    setError("");
    try { await fn(...args); await load(); } catch (e) { setError(e.message); }
  };
  const publishLesson = act(() => api(`/lessons/${id}/publish`, { method: "POST" }));
  const publish = act((exId) => api(`/exercises/${exId}/publish`, { method: "POST" }));
  const remove = act((exId) => api(`/exercises/${exId}`, { method: "DELETE" }));

  if (!lesson) return <p className="error">{error}</p>;
  const drafts = exercises.filter((e) => e.status === "brouillon").length;

  return (
    <>
      <p><Link to="/formateur/cours">← Cours</Link></p>
      <section className="card stack">
        <div className="row">
          <input className="grow" value={lesson.title} onChange={(e) => setLesson({ ...lesson, title: e.target.value })} />
          <span className={`badge ${lesson.status}`}>{LABELS[lesson.status]}</span>
        </div>
        <textarea style={{ minHeight: 200 }} value={lesson.content}
                  onChange={(e) => setLesson({ ...lesson, content: e.target.value })} placeholder="Contenu de la leçon (Markdown)" />
        <div className="row">
          <button onClick={saveLesson}>Enregistrer</button>
          {lesson.status !== "publie" && <button className="ghost" onClick={publishLesson}>Publier la leçon</button>}
          <span className="ok">{saved}</span>
        </div>
      </section>

      <AiGenerator lessonId={lesson.id} onDone={load} />

      <section className="card stack">
        <div className="row">
          <h2 className="grow">Exercices</h2>
          {drafts > 0 && <span className="badge brouillon">{drafts} à relire</span>}
          <button className="ghost" onClick={() => setEditing("new")}>+ Exercice</button>
        </div>
        {error && <p className="error">{error}</p>}

        {editing === "new" && (
          <div className="card">
            <ExerciseForm submitLabel="Créer" onCancel={() => setEditing(null)}
              onSubmit={async (body) => { await api(`/lessons/${id}/exercises`, { method: "POST", body }); setEditing(null); load(); }} />
          </div>
        )}

        {exercises.map((ex) => (
          <div className="card" key={ex.id}>
            {editing === ex.id ? (
              <ExerciseForm initial={ex} onCancel={() => setEditing(null)}
                onSubmit={async (body) => { await api(`/exercises/${ex.id}`, { method: "PATCH", body }); setEditing(null); load(); }} />
            ) : (
              <>
                <div className="row">
                  <strong className="grow">{ex.title}</strong>
                  {ex.generated_by_ai && <span className="badge ia">Généré par IA</span>}
                  <span className="badge">{LABELS[ex.type]} · {LABELS[ex.difficulty]} · {ex.notion}</span>
                  <span className={`badge ${ex.status}`}>{LABELS[ex.status]}</span>
                </div>
                <p>{ex.statement}</p>
                {ex.choices && <ul>{ex.choices.map((c) => <li key={c}>{c === ex.solution ? <strong>{c} ✓</strong> : c}</li>)}</ul>}
                {!ex.choices && <details><summary>Corrigé</summary><pre>{ex.solution}</pre></details>}
                <div className="row">
                  <button className="ghost" onClick={() => setEditing(ex.id)}>Modifier</button>
                  {ex.status === "brouillon" && <button onClick={() => publish(ex.id)}>Valider et publier</button>}
                  <button className="danger" onClick={() => confirm("Supprimer cet exercice ?") && remove(ex.id)}>Supprimer</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>
    </>
  );
}

function AiGenerator({ lessonId, onDone }) {
  const [f, setF] = useState({ consigne: "", count: 5, difficulty: "debutant", type: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const generate = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      const res = await api("/ai/generate", {
        method: "POST",
        body: { lesson_id: lessonId, consigne: f.consigne, count: Number(f.count), difficulty: f.difficulty, type: f.type || null },
      });
      setMsg(`${res.created.length} exercice(s) ajouté(s) en brouillon` + (res.rejected ? `, ${res.rejected} écarté(s) car invalides` : "") + ".");
      onDone();
    } catch (err) { setMsg(err.message); }
    finally { setBusy(false); }
  };

  return (
    <form className="card stack" onSubmit={generate}>
      <h2>Générer des exercices avec l'IA</h2>
      <textarea placeholder="Ex. : 5 exercices sur les boucles en Python, avec des cas de range() et de break" value={f.consigne}
                onChange={set("consigne")} required style={{ minHeight: 60 }} />
      <div className="row">
        <label>Nombre<input type="number" min="1" max="20" value={f.count} onChange={set("count")} /></label>
        <label>Niveau
          <select value={f.difficulty} onChange={set("difficulty")}>
            <option value="debutant">Débutant</option><option value="intermediaire">Intermédiaire</option><option value="avance">Avancé</option>
          </select>
        </label>
        <label>Type
          <select value={f.type} onChange={set("type")}>
            <option value="">Au choix</option><option value="qcm">QCM</option><option value="code">Code</option><option value="texte">Texte libre</option>
          </select>
        </label>
      </div>
      <p className="notice">Les exercices générés arrivent en <strong>brouillon</strong>. Ils ne sont visibles des apprenants
        qu'après relecture et validation : vous restez responsable du contenu.</p>
      <div className="row">
        <button disabled={busy}>{busy ? "Génération…" : "Générer"}</button>
        <span className="muted">{msg}</span>
      </div>
    </form>
  );
}
