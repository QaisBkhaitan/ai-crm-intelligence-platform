import { Outlet } from "react-router-dom";
import AppNavbar from "./AppNavbar";

function AppLayout() {
  return (
    <div className="app-shell">
      <AppNavbar />
      <main className="app-main">
        <div className="app-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default AppLayout;