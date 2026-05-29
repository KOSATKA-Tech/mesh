import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import Nodes from './pages/Nodes';
import Settings from './pages/Settings';
import Alerts from './pages/Alerts';
import Login from './pages/Login';
import Setup from './pages/Setup';
import Layout from './components/Layout';
import { AuthProvider, useAuth } from './context/AuthContext';

QueryClientProvider({
  client: new QueryClient()
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <div className="flex h-screen items-center justify-center bg-background text-foreground">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/setup" element={<Setup />} />
            
            <Route path="/" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route index element={<Dashboard />} />
              <Route path="nodes" element={<Nodes />} />
              <Route path="settings" element={<Settings />} />
              <Route path="alerts" element={<Alerts />} />
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
