import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, LABELS } from "../../api";

export default function Courses() {
  const [courses, setCourses] = useState([]);
  const [lessons, setLessons] = useState({});
  const [title, setTitle] = useState("");
  const [lessonTitle, setLessonTitle] = useState({});
  const [error, setError] = useState("");

  const load = async () => {
    const cs = await api("/courses");
    setCourses(cs);
    const entries = await Promise.all(cs.map(async (c) => [c.id, await api(`/courses/${c.id}/lessons`)]));
    setLessons(Object.fromEntries(entries));
  };
  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  const createCourse = async (e) => {
    e.preventDefault();
    await api("/courses", { method: "POST", body: { title } }).catch((e) => setError(e.message));
    setTitle("");
    load();
  };

  const createLesson = async (courseId) => {
    const t = lessonTitle[courseId];
    if (!t) return;
    await api(`/courses/${courseId}/lessons`, { method: "POST", body: { title: t } }).catch((e) => setError(e.message));
    setLessonTitle({ ...lessonTitle, [courseId]: "" });
    load();
  };

  return (
    <>
      <h1>Cours & exercices</h1>
      {error && <p className="error">{error}</p>}
      <form className="card row" onSubmit={createCourse}>
        <input className="grow" placeholder="Nouvelle matière (ex. Python — débutant)" value={title}
               onChange={(e) => setTitle(e.target.value)} required />
        <button>Créer le cours</button>
      </form>

      {courses.map((c) => (
        <section className="card" key={c.id}>
          <h2>{c.title}</h2>
          <ul>
            {(lessons[c.id] || []).map((l) => (
              <li key={l.id}>
                <Link to={`/formateur/lecons/${l.id}`}>{l.title}</Link>{" "}
                <span className={`badge ${l.status}`}>{LABELS[l.status]}</span>
              </li>
            ))}
          </ul>
          <div className="row">
            <input className="grow" placeholder="Nouvelle leçon" value={lessonTitle[c.id] || ""}
                   onChange={(e) => setLessonTitle({ ...lessonTitle, [c.id]: e.target.value })} />
            <button className="ghost" onClick={() => createLesson(c.id)}>Ajouter la leçon</button>
          </div>
        </section>
      ))}
    </>
  );
}
