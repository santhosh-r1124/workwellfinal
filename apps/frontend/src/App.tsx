import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import Admin from "./pages/Admin";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import PatternTimeline from "./pages/PatternTimeline";
import PrivacyCenter from "./pages/PrivacyCenter";
import TeamAnalytics from "./pages/TeamAnalytics";
import ManagementLogin from "./pages/ManagementLogin";
import ManagementHR from "./pages/ManagementHR";
import ManagementManager from "./pages/ManagementManager";
import ManagementConsultant from "./pages/ManagementConsultant";

// Managers have no personal dashboard in this product - their view is the
// team aggregate - so their home is Team analytics.
function Home() {
  const { user } = useAuth();
  if (user?.role === "manager") return <Navigate to="/teams" replace />;
  return <Dashboard />;
}

const PAGES: { path: string; element: React.ReactElement }[] = [
  { path: "/", element: <Home /> },
  { path: "/timeline", element: <PatternTimeline /> },
  { path: "/privacy", element: <PrivacyCenter /> },
  { path: "/teams", element: <TeamAnalytics /> },
  { path: "/admin", element: <Admin /> },
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/management" element={<ManagementLogin />} />
      <Route path="/management/hr" element={<ManagementHR />} />
      <Route path="/management/manager" element={<ManagementManager />} />
      <Route path="/management/consultant" element={<ManagementConsultant />} />
      {PAGES.map(({ path, element }) => (
        <Route
          key={path}
          path={path}
          element={
            <ProtectedRoute>
              <AppShell>{element}</AppShell>
            </ProtectedRoute>
          }
        />
      ))}
    </Routes>
  );
}
