import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import CustomerDetails from "./pages/CustomerDetails";
import AIChat from "./pages/AIChat";
import DataImport from "./pages/DataImport";
import SocialListener from "./pages/SocialListener";
import ActionCenter from "./pages/ActionCenter";
function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/customers/:id" element={<CustomerDetails />} />
        <Route path="/ai-chat" element={<AIChat />} />
        <Route path="/data-import" element={<DataImport />} />
        <Route path="/social" element={<SocialListener />} />
        <Route path="/actions" element={<ActionCenter />} />
      </Route>
    </Routes>
  );
}

export default App;