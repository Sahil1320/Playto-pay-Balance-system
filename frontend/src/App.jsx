import { useState, useEffect, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { isAuthenticated } from './api/client';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [authState, setAuthState] = useState(isAuthenticated());

  const handleLoginSuccess = useCallback(() => {
    setAuthState(true);
  }, []);

  const handleLogout = useCallback(() => {
    setAuthState(false);
  }, []);

  return (
    <div className="min-h-screen bg-surface-950">
      <Routes>
        <Route
          path="/login"
          element={
            authState ? (
              <Navigate to="/" replace />
            ) : (
              <LoginPage onLoginSuccess={handleLoginSuccess} />
            )
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
