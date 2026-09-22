import { Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import Admin from "./pages/Admin";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import PatternTimeline from "./pages/PatternTimeline";
import PrivacyCenter from "./pages/PrivacyCenter";
import TeamAnalytics from "./pages/TeamAnalytics";

const PAGES: { path: string; element: React.ReactElement }[] = [
  { path: "/", element: <Dashboard /> },
  { path: "/timeline", element: <PatternTimeline /> },
  { path: "/privacy", element: <PrivacyCenter /> },
  { path: "/teams", element: <TeamAnalytics /> },
  { path: "/admin", element: <Admin /> },
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
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
