import { NavLink } from "react-router-dom";

function AppNavbar() {
  return (
    <header className="app-navbar">
      <div className="app-container app-navbar-inner">
        <NavLink to="/" className="brand">
          <div className="brand-mark">AI</div>
          <div className="brand-text">
            <span className="brand-title">CRM Intelligence</span>
            <span className="brand-subtitle">Fullstack AI Platform</span>
          </div>
        </NavLink>

        <nav className="nav-links">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            Dashboard
          </NavLink>

          <NavLink
            to="/customers"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            Customers
          </NavLink>

          <NavLink
            to="/ai-chat"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            AI Assistant
          </NavLink>

          <NavLink
            to="/data-import"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            Data Import
          </NavLink>

          <NavLink
            to="/social"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            Social Listener
          </NavLink>
          <NavLink
            to="/actions"
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            Action Center
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default AppNavbar;