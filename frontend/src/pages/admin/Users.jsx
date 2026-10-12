import { useEffect, useState } from "react";
import { api } from "../../api";

const EMPTY = { email: "", full_name: "", password: "", role: "apprenant" };

export default function Users() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const load = () => api("/users").then(setUsers).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api("/users", { method: "POST", body: form });
      setForm(EMPTY);
      load();
    } catch (err) { setError(err.message); }
  };

  const patch = async (id, body) => {
    try { await api(`/users/${id}`, { method: "PATCH", body }); load(); }
    catch (err) { setError(err.message); }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <h1>Utilisateurs</h1>
      {error && <p className="error">{error}</p>}
      <form className="card row" onSubmit={create}>
        <input className="grow" placeholder="Nom complet" value={form.full_name} onChange={set("full_name")} required />
        <input className="grow" placeholder="Email" value={form.email} onChange={set("email")} required />
        <input className="grow" placeholder="Mot de passe" type="password" value={form.password} onChange={set("password")} required />
        <select style={{ width: "auto" }} value={form.role} onChange={set("role")}>
          <option value="apprenant">Apprenant</option>
          <option value="formateur">Formateur</option>
          <option value="admin">Admin</option>
        </select>
        <button>Créer</button>
      </form>
      <div className="card">
        <table>
          <thead><tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Actif</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <select value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}>
                    <option value="apprenant">apprenant</option>
                    <option value="formateur">formateur</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td>
                  <input type="checkbox" style={{ width: "auto" }} checked={u.is_active}
                         onChange={(e) => patch(u.id, { is_active: e.target.checked })} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
