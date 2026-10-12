import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { homeFor, useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("formateur@demo.fr");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const user = await login(email, password);
      navigate(homeFor(user.role));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="card stack" style={{ maxWidth: 380, margin: "80px auto" }} onSubmit={submit}>
      <h1>Connexion</h1>
      <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label>Mot de passe<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {error && <p className="error">{error}</p>}
      <button>Se connecter</button>
      <p className="muted">Démo : admin@, formateur@, alice@, bob@, chloe@demo.fr — mot de passe demo1234</p>
    </form>
  );
}
