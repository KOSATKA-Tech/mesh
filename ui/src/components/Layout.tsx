import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

export default function Layout() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Network' },
    { to: '/nodes', icon: Server, label: 'Nodes' },
    { to: '/alerts', icon: Bell, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-white/10">
      {/* Mobile Top Bar */}
      <div className="lg:hidden absolute top-0 left-0 right-0 h-16 border-b border-border bg-background/50 backdrop-blur-xl flex items-center justify-between px-6 z-50">
        <div className="flex items-center space-x-3">
          <img src="/logo.png" alt="Kosatka" className="h-7 w-auto glow-white" />
          <span className="font-bold tracking-luxury uppercase italic text-[10px] text-white/40">Kosatka</span>
        </div>
        <button 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/60"
        >
          {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Sidebar / Mobile Overlay */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-40 w-72 border-r border-border bg-background/80 backdrop-blur-2xl flex flex-col transform transition-transform duration-500 ease-in-out lg:relative lg:translate-x-0 lg:bg-transparent lg:backdrop-blur-none",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="p-10 hidden lg:flex flex-col items-center space-y-4">
          <img src="/logo.png" alt="Kosatka" className="h-16 w-auto glow-white" />
          <div className="text-[10px] font-bold tracking-luxury uppercase italic text-white/20 text-center">
            Infrastructure <br/> Control Plane
          </div>
        </div>

        <nav className="flex-1 px-8 py-20 lg:py-6 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeMobileMenu}
              className={({ isActive }) => clsx(
                "flex items-center space-x-4 px-5 py-3.5 rounded-2xl transition-all duration-300 group relative",
                isActive 
                  ? "bg-white/5 text-white shadow-[0_0_20px_rgba(255,255,255,0.02)]" 
                  : "text-white/30 hover:text-white/60 hover:bg-white/[0.02]"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={clsx("h-4 w-4 transition-transform duration-500 group-hover:scale-110")} />
                  <span className="font-bold uppercase tracking-widest text-[10px]">{item.label}</span>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="absolute left-0 w-1 h-4 bg-white rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-8 border-t border-border/50 space-y-6 bg-white/[0.01]">
          <div className="flex items-center space-x-4 px-2">
            <div className="h-10 w-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center font-bold text-white/60 text-xs transition-transform hover:scale-105">
              {user?.username?.[0].toUpperCase() || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-widest text-white/80 truncate">{user?.username || 'Admin'}</p>
              <p className="text-[9px] font-medium tracking-tight text-white/20 truncate lowercase">{user?.email || 'System Master'}</p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 text-white/20 hover:text-white transition-all rounded-xl border border-white/5 hover:bg-white/5 hover:border-white/10"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="font-bold text-[9px] uppercase tracking-widest">Terminate Session</span>
          </button>
        </div>
      </aside>

      {/* Mobile Overlay Backdrop */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-md z-30 lg:hidden transition-opacity duration-500"
          onClick={closeMobileMenu}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative pt-16 lg:pt-0 bg-background">
        {/* Subtle radial glow */}
        <div className="absolute top-[-10%] left-1/4 w-[120%] h-[120%] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-from)_0%,_transparent_60%)] from-ocean-blue/10 pointer-events-none -z-10" />
        
        <div className="container mx-auto p-6 lg:p-12 max-w-7xl relative">
           <Outlet />
        </div>
      </main>
    </div>
  );
}
