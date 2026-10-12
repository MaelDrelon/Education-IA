import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth";
import Login from "./pages/Login";
import Users from "./pages/admin/Users";
import Courses from "./pages/formateur/Courses";
import LessonEditor from "./pages/formateur/LessonEditor";
import Exams from "./pages/formateur/Exams";
import Analytics from "./pages/formateur/Analytics";
import MyExams from "./pages/apprenant/MyExams";
import TakeExam from "./pages/apprenant/TakeExam";

const NAV = {
  admin: [["/admin/utilisateurs", "Utilisateurs"]],
  formateur: [
    ["/formateur/cours", "Cours & exercices"],
    ["/formateur/examens", "Examens"],
    ["/formateur/analyse", "Analyse IA"],
  ],
  apprenant: [["/apprenant/examens", "Mes examens"]],
};

function Guard({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

export default function App() {
  const { user, ready, logout } = useAuth();
  if (!ready) return null;

  const staff = ["formateur", "admin"];
  return (
    <>
      {user && (
        <header className="topbar">
          <strong>Edu IA</strong>
          <nav>
            {NAV[user.role].map(([to, label]) => (
              <NavLink key={to} to={to}>{label}</NavLink>
            ))}
          </nav>
          <span className="muted">{user.full_name} · {user.role}</span>
          <button className="ghost" onClick={logout}>Déconnexion</button>
        </header>
      )}
      <main className="container">
        <Routes>
          <Route path="/login" element={user ? <Navigate to={homeFor(user.role)} /> : <Login />} />
          <Route path="/admin/utilisateurs" element={<Guard roles={["admin"]}><Users /></Guard>} />
          <Route path="/formateur/cours" element={<Guard roles={staff}><Courses /></Guard>} />
          <Route path="/formateur/lecons/:id" element={<Guard roles={staff}><LessonEditor /></Guard>} />
          <Route path="/formateur/examens" element={<Guard roles={staff}><Exams /></Guard>} />
          <Route path="/formateur/analyse" element={<Guard roles={staff}><Analytics /></Guard>} />
          <Route path="/apprenant/examens" element={<Guard roles={["apprenant"]}><MyExams /></Guard>} />
          <Route path="/apprenant/examens/:id" element={<Guard roles={["apprenant"]}><TakeExam /></Guard>} />
          <Route path="*" element={<Navigate to={user ? homeFor(user.role) : "/login"} replace />} />
        </Routes>
      </main>
    </>
  );
}
