import { useEffect, useState } from "react";
import { api, LABELS } from "../../api";

export default function Exams() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [exams, setExams] = useState([]);
  const [exercises, setExercises] = useState([]);
  const [learners, setLearners] = useState([]);
  const [form, setForm] = useState({ title: "", scheduled_at: "", duration_minutes: 60, exercise_ids: [] });
  const [error, setError] = useState("");

  useEffect(() => {
    api("/courses").then((cs) => { setCourses(cs); if (cs[0]) setCourseId(String(cs[0].id)); }).catch((e) => setError(e.message));
    api("/users?role=apprenant").then(setLearners).catch(() => {});
  }, []);

  const load = async () => {
    if (!courseId) return;
    setExams(await api(`/exams?course_id=${courseId}`));
    setExercises(await api(`/courses/${courseId}/exercises?published_only=true`));
  };
  useEffect(() => { load().catch((e) => setError(e.message)); }, [courseId]);

  const toggle = (list, id) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  const act = (fn) => async (...args) => {
    setError("");
    try { await fn(...args); await load(); } catch (e) { setError(e.message); }
  };

  const create = act(async (e) => {
    e.preventDefault();
    await api(`/courses/${courseId}/exams`, { method: "POST", body: { ...form, duration_minutes: Number(form.duration_minutes) } });
    setForm({ title: "", scheduled_at: "", duration_minutes: 60, exercise_ids: [] });
  });
  const assign = act((examId, userIds) => api(`/exams/${examId}/assign`, { method: "POST", body: { user_ids: userIds } }));
  const publish = act((examId) => api(`/exams/${examId}/publish`, { method: "POST" }));

  return (
    <>
      <h1>Examens</h1>
      <div className="row card">
        <span>Cours</span>
        <select style={{ width: "auto" }} value={courseId} onChange={(e) => setCourseId(e.target.value)}>
          {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </div>
      {error && <p className="error">{error}</p>}

      <form className="card stack" onSubmit={create}>
        <h2>Nouvel examen</h2>
        <div className="row">
          <label className="grow">Titre<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
          <label>Date<input type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} required /></label>
          <label>Durée (min)<input type="number" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} /></label>
        </div>
        <span className="muted">Exercices validés disponibles</span>
        {exercises.length === 0 && <p className="muted">Aucun exercice publié dans ce cours.</p>}
        {exercises.map((ex) => (
          <label key={ex.id} className="row" style={{ display: "flex" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={form.exercise_ids.includes(ex.id)}
                   onChange={() => setForm({ ...form, exercise_ids: toggle(form.exercise_ids, ex.id) })} />
            {ex.title} <span className="badge">{LABELS[ex.type]} · {ex.notion}</span>
          </label>
        ))}
        <button disabled={!form.exercise_ids.length}>Créer l'examen</button>
      </form>

      {exams.map((exam) => (
        <ExamCard key={exam.id} exam={exam} learners={learners} onAssign={assign} onPublish={publish} />
      ))}
    </>
  );
}

function ExamCard({ exam, learners, onAssign, onPublish }) {
  const [selected, setSelected] = useState([]);
  const assigned = new Set(exam.assigned_user_ids);
  const available = learners.filter((l) => !assigned.has(l.id));

  return (
    <section className="card stack">
      <div className="row">
        <h2 className="grow">{exam.title}</h2>
        <span className="muted">{new Date(exam.scheduled_at).toLocaleString("fr-FR")} · {exam.duration_minutes} min</span>
        <span className={`badge ${exam.status}`}>{LABELS[exam.status]}</span>
        {exam.status !== "publie" && <button onClick={() => onPublish(exam.id)}>Publier</button>}
      </div>
      <span className="muted">{exam.exercises.length} exercice(s) · assigné à : {
        learners.filter((l) => assigned.has(l.id)).map((l) => l.full_name).join(", ") || "personne"}</span>
      {available.length > 0 && (
        <div className="row">
          {available.map((l) => (
            <label key={l.id} className="row" style={{ display: "flex" }}>
              <input type="checkbox" style={{ width: "auto" }} checked={selected.includes(l.id)}
                     onChange={() => setSelected(selected.includes(l.id) ? selected.filter((x) => x !== l.id) : [...selected, l.id])} />
              {l.full_name}
            </label>
          ))}
          <button className="ghost" disabled={!selected.length} onClick={() => { onAssign(exam.id, selected); setSelected([]); }}>Assigner</button>
        </div>
      )}
    </section>
  );
}
