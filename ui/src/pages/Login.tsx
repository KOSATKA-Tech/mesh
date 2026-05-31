import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Lock, User } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if setup is needed
    axios.get('/api/v1/auth/me').catch(() => {
      // Just keep it simple
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);
      
      const resp = await axios.post('/api/v1/auth/login', formData);
      login(resp.data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid username or password');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md space-y-8 bg-card/50 backdrop-blur-xl p-8 rounded-2xl border border-border shadow-2xl relative"
      >
        <div className="text-center">
          <img src="/admin/logo-main.png" alt="Kosatka" className="mx-auto h-20 w-auto mb-4 filter brightness-200 contrast-150 mix-blend-screen drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]" />
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Master Node
          </h2>
          <p className="mt-2 text-muted-foreground">
            Sign in to your KOSATKA account
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                required
                className="w-full bg-background/50 border border-border rounded-lg py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="password"
                required
                className="w-full bg-background/50 border border-border rounded-lg py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-destructive text-sm font-medium bg-destructive/10 p-3 rounded-lg border border-destructive/20"
            >
              {error}
            </motion.p>
          )}

          <button
            type="submit"
            className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-lg hover:opacity-90 active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)]"
          >
            Access Control Plane
          </button>
          
          <div className="text-center">
            <button 
              type="button"
              onClick={() => navigate('/setup')}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              First time here? Run Setup
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
