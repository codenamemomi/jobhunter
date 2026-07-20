import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../store/AuthContext";

const links = [
  { to: "/", label: "Search", end: true },
  { to: "/matches", label: "Matches" },
  { to: "/saved", label: "Saved" },
  { to: "/tracker", label: "Tracker" },
  { to: "/cv", label: "CV" },
];

export default function Layout() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">JH</span>
          <div>
            <strong>JobHunter</strong>
            <span className="brand-sub">Jobs · Alerts · Tracker</span>
          </div>
        </div>

        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="topbar-actions">
          {isAuthenticated ? (
            <>
              <span className="user-chip" title={user?.email}>
                {user?.full_name || user?.email}
              </span>
              <button type="button" className="btn btn-ghost" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <NavLink to="/login" className="btn btn-primary">
              Sign in
            </NavLink>
          )}
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <span>JobHunter · aggregate · track · apply</span>
      </footer>
    </div>
  );
}
