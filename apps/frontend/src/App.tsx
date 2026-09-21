import { Route, Routes } from "react-router-dom";

import NavBar from "./components/NavBar";
import ProtectedRoute from "./components/ProtectedRoute";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import PatternTimeline from "./pages/PatternTimeline";
import PrivacyCenter from "./pages/PrivacyCenter";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950">
      <NavBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/timeline"
          element={
            <ProtectedRoute>
              <PatternTimeline />
            </ProtectedRoute>
          }
        />
        <Route
          path="/privacy"
          element={
            <ProtectedRoute>
              <PrivacyCenter />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}
