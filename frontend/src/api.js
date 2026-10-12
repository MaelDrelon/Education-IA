const BASE = import.meta.env.VITE_API_URL || "/api";

export const getToken = () => localStorage.getItem("token");
export const setToken = (t) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token"));

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(BASE + path, { method, headers, body: payload });
  if (res.status === 401) setToken(null);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : j.detail?.map?.((d) => d.msg).join(", ") || msg;
    } catch {
      /* corps non JSON */
    }
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

export const LABELS = {
  debutant: "Débutant",
  intermediaire: "Intermédiaire",
  avance: "Avancé",
  qcm: "QCM",
  code: "Code",
  texte: "Texte libre",
  brouillon: "Brouillon",
  publie: "Publié",
};
