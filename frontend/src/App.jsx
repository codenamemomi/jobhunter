import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Search from "./pages/Search";
import Saved from "./pages/Saved";
import Tracker from "./pages/Tracker";
import CV from "./pages/CV";
import Matches from "./pages/Matches";
import Queue from "./pages/Queue";
import { useAuth } from "./store/AuthContext";

export default function App() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading JobHunter…</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route index element={<Search />} />
        <Route
          path="saved"
          element={
            <ProtectedRoute>
              <Saved />
            </ProtectedRoute>
          }
        />
        <Route
          path="tracker"
          element={
            <ProtectedRoute>
              <Tracker />
            </ProtectedRoute>
          }
        />
        <Route
          path="cv"
          element={
            <ProtectedRoute>
              <CV />
            </ProtectedRoute>
          }
        />
        <Route
          path="matches"
          element={
            <ProtectedRoute>
              <Matches />
            </ProtectedRoute>
          }
        />
        <Route
          path="queue"
          element={
            <ProtectedRoute>
              <Queue />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
