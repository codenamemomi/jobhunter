import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../store/AuthContext";

const links = [
  { to: "/", label: "Search", end: true },
  { to: "/matches", label: "Matches" },
  { to: "/queue", label: "Queue" },
  { to: "/saved", label: "Saved" },
  { to: "/tracker", label: "Tracker" },
  { to: "/cv", label: "CV" },
];

export default function Layout() {
  const { user, isAuthenticated, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Close drawer on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Lock body scroll when menu open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const displayName = user?.full_name || user?.email || "";

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-row">
          <NavLink to="/" className="brand" onClick={() => setMenuOpen(false)}>
            <span className="brand-mark">JH</span>
            <div className="brand-text">
              <strong>JobHunter</strong>
              <span className="brand-sub">Jobs · Alerts · Tracker</span>
            </div>
          </NavLink>

          {/* Desktop nav */}
          <nav className="nav nav-desktop" aria-label="Main">
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

          <div className="topbar-actions topbar-actions-desktop">
            {isAuthenticated ? (
              <>
                <span className="user-chip" title={user?.email}>
                  {displayName}
                </span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
                  Log out
                </button>
              </>
            ) : (
              <NavLink to="/login" className="btn btn-primary btn-sm">
                Sign in
              </NavLink>
            )}
          </div>

          <button
            type="button"
            className={`menu-toggle ${menuOpen ? "open" : ""}`}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </header>

      {/* Mobile drawer */}
      <div
        className={`nav-drawer-backdrop ${menuOpen ? "open" : ""}`}
        onClick={() => setMenuOpen(false)}
        aria-hidden={!menuOpen}
      />
      <aside className={`nav-drawer ${menuOpen ? "open" : ""}`} aria-hidden={!menuOpen}>
        <div className="nav-drawer-head">
          <span className="nav-drawer-title">Menu</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setMenuOpen(false)}
          >
            Close
          </button>
        </div>

        {isAuthenticated && (
          <div className="nav-drawer-user">
            <span className="nav-drawer-user-name">{displayName}</span>
            <span className="nav-drawer-user-email">{user?.email}</span>
          </div>
        )}

        <nav className="nav-drawer-links" aria-label="Mobile">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                isActive ? "nav-drawer-link active" : "nav-drawer-link"
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="nav-drawer-footer">
          {isAuthenticated ? (
            <button
              type="button"
              className="btn btn-ghost btn-block"
              onClick={() => {
                setMenuOpen(false);
                logout();
              }}
            >
              Log out
            </button>
          ) : (
            <NavLink
              to="/login"
              className="btn btn-primary btn-block"
              onClick={() => setMenuOpen(false)}
            >
              Sign in
            </NavLink>
          )}
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <span>JobHunter · aggregate · track · apply</span>
      </footer>
    </div>
  );
}
