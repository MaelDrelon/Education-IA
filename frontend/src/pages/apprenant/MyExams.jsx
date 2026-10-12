import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";

export default function MyExams() {
  const [exams, setExams] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => { api("/exams").then(setExams).catch((e) => setError(e.message)); }, []);

  return (
    <>
      <h1>Mes examens</h1>
      {error && <p className="error">{error}</p>}
      {exams.length === 0 && <p className="muted">Aucun examen ne vous est assigné pour le moment.</p>}
      {exams.map((e) => (
        <div className="card row" key={e.id}>
          <div className="grow">
            <strong>{e.title}</strong>
            <div className="muted">{new Date(e.scheduled_at).toLocaleString("fr-FR")} · {e.duration_minutes} min · {e.exercises.length} exercice(s)</div>
          </div>
          <Link to={`/apprenant/examens/${e.id}`}>Ouvrir</Link>
        </div>
      ))}
    </>
  );
}
