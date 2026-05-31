import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, User, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Setup() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const resp = await axios.post('/api/v1/auth/setup', {
        username,
        password,
        email
      });
      setSuccess(true);
      setTimeout(() => {
        login(resp.data.access_token);
        navigate('/');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Setup failed. Admin might already exist.');
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-center space-y-4 bg-card/50 backdrop-blur-xl p-12 rounded-3xl border border-primary/20 shadow-[0_0_50px_rgba(34,197,94,0.1)]"
        >
          <CheckCircle2 className="mx-auto h-20 w-20 text-green-500 mb-4" />
          <h2 className="text-3xl font-bold text-foreground">Welcome, Commander</h2>
          <p className="text-muted-foreground">Admin account created. Redirecting to bridge...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-green-500/5 rounded-full blur-[120px] pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md space-y-8 bg-card/50 backdrop-blur-xl p-8 rounded-2xl border border-border shadow-2xl relative"
      >
        <div className="text-center">
          <img src="/admin/logo-main.png" alt="Kosatka" className="mx-auto h-20 w-auto mb-4 filter brightness-200 contrast-150 mix-blend-screen" />
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Initialize Mesh
          </h2>
          <p className="mt-2 text-muted-foreground">
            Create the primary Super-Admin account
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                required
                className="w-full bg-background/50 border border-border rounded-lg py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-green-500/50 focus:border-transparent transition-all outline-none"
                placeholder="Admin Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="email"
                required
                className="w-full bg-background/50 border border-border rounded-lg py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-green-500/50 focus:border-transparent transition-all outline-none"
                placeholder="Admin Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <input
                type="password"
                required
                className="w-full bg-background/50 border border-border rounded-lg py-3 pl-10 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-green-500/50 focus:border-transparent transition-all outline-none"
                placeholder="Master Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className="text-destructive text-sm font-medium bg-destructive/10 p-3 rounded-lg border border-destructive/20">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-foreground text-background font-bold py-3 rounded-lg hover:opacity-90 active:scale-[0.98] transition-all"
          >
            Deploy Administrator
          </button>
        </form>
      </motion.div>
    </div>
  );
}
