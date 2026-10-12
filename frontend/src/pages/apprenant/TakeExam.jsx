import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, LABELS } from "../../api";

export default function TakeExam() {
  const { id } = useParams();
  const [exam, setExam] = useState(null);
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState({}); // exerciseId -> score (null = à corriger)
  const [error, setError] = useState("");

  useEffect(() => { api(`/exams/${id}`).then(setExam).catch((e) => setError(e.message)); }, [id]);

  const submit = async (ex) => {
    setError("");
    try {
      const attempt = await api("/attempts", {
        method: "POST",
        body: { exercise_id: ex.id, exam_id: exam.id, answer: answers[ex.id] || "" },
      });
      setResults({ ...results, [ex.id]: attempt.score });
    } catch (e) { setError(e.message); }
  };

  if (!exam) return <p className="error">{error}</p>;
  const done = new Set([...exam.done_exercise_ids, ...Object.keys(results).map(Number)]);

  return (
    <>
      <p><Link to="/apprenant/examens">← Mes examens</Link></p>
      <h1>{exam.title}</h1>
      <p className="muted">{done.size} / {exam.exercises.length} exercice(s) rendu(s)</p>
      {error && <p className="error">{error}</p>}

      {exam.exercises.map((ex, i) => (
        <section className="card stack" key={ex.id}>
          <div className="row">
            <strong className="grow">{i + 1}. {ex.title}</strong>
            <span className="badge">{LABELS[ex.type]}</span>
          </div>
          <p>{ex.statement}</p>

          {done.has(ex.id) ? (
            <Result score={results[ex.id]} known={ex.id in results} />
          ) : (
            <>
              {ex.type === "qcm" ? (
                ex.choices.map((c) => (
                  <label key={c} className="row" style={{ display: "flex" }}>
                    <input type="radio" style={{ width: "auto" }} name={`ex-${ex.id}`} checked={answers[ex.id] === c}
                           onChange={() => setAnswers({ ...answers, [ex.id]: c })} />
                    {c}
                  </label>
                ))
              ) : (
                <textarea className={ex.type === "code" ? "code" : ""} value={answers[ex.id] || ""}
                          onChange={(e) => setAnswers({ ...answers, [ex.id]: e.target.value })} />
              )}
              <div><button disabled={!answers[ex.id]} onClick={() => submit(ex)}>Rendre</button></div>
            </>
          )}
        </section>
      ))}
    </>
  );
}

function Result({ score, known }) {
  if (!known) return <p className="muted">Déjà rendu.</p>;
  if (score === null) return <p className="muted">Rendu — en attente de correction par le formateur.</p>;
  return score >= 1 ? <p className="ok">Bonne réponse ✓</p> : <p className="error">Réponse incorrecte</p>;
}
