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
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-white/10 antialiased">
      {/* Mobile Top Bar */}
      <div className="lg:hidden absolute top-0 left-0 right-0 h-16 border-b border-white/5 bg-background/50 backdrop-blur-xl flex items-center justify-between px-6 z-50">
        <div className="flex items-center space-x-3">
          <img src="/logo-main.png" alt="Kosatka" className="h-8 w-auto mix-blend-screen brightness-200" />
          <span className="font-bold tracking-[0.3em] uppercase italic text-[10px] text-white/40">Kosatka</span>
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
        "fixed inset-y-0 left-0 z-40 w-72 border-r border-white/5 bg-background/90 backdrop-blur-3xl flex flex-col transform transition-transform duration-500 ease-in-out lg:relative lg:translate-x-0 lg:bg-transparent lg:backdrop-blur-none",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="p-12 hidden lg:flex flex-col items-center space-y-6">
          <motion.img 
            whileHover={{ scale: 1.05, filter: "brightness(250%)" }}
            src="/logo-main.png" 
            alt="Kosatka" 
            className="h-20 w-auto mix-blend-screen brightness-200 drop-shadow-[0_0_30px_rgba(255,255,255,0.1)] transition-all duration-700" 
          />
          <div className="space-y-1">
            <div className="text-[10px] font-black uppercase tracking-[0.5em] italic text-white/40 text-center">
              Infrastructure
            </div>
            <div className="text-[8px] font-bold tracking-[0.3em] uppercase text-white/20 text-center">
              Control Plane v1.0
            </div>
          </div>
        </div>

        <nav className="flex-1 px-8 py-20 lg:py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeMobileMenu}
              className={({ isActive }) => clsx(
                "flex items-center space-x-5 px-6 py-4 rounded-2xl transition-all duration-500 group relative",
                isActive 
                  ? "bg-white/[0.03] text-white shadow-[0_0_30px_rgba(255,255,255,0.01)]" 
                  : "text-white/20 hover:text-white/50 hover:bg-white/[0.01]"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={clsx("h-4 w-4 transition-all duration-500", isActive ? "text-white scale-110" : "group-hover:scale-105")} />
                  <span className="font-bold uppercase tracking-[0.2em] text-[10px] italic">{item.label}</span>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="absolute left-0 w-1 h-5 bg-white/40 rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-8 border-t border-white/5 space-y-8 bg-white/[0.005]">
          <div className="flex items-center space-x-4 px-2">
            <div className="h-10 w-10 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center font-bold text-white/40 text-xs transition-all hover:scale-105 hover:bg-white/10">
              {user?.username?.[0].toUpperCase() || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-black uppercase tracking-widest text-white/70 truncate">{user?.username || 'Admin'}</p>
              <p className="text-[8px] font-bold tracking-tight text-white/10 truncate lowercase italic">{user?.email || 'System Master'}</p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full flex items-center justify-center space-x-3 px-4 py-3.5 text-white/10 hover:text-white/80 transition-all rounded-2xl border border-white/0 hover:border-white/5 hover:bg-white/[0.02]"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="font-bold text-[9px] uppercase tracking-[0.3em]">Terminate</span>
          </button>
        </div>
      </aside>

      {/* Mobile Overlay Backdrop */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-xl z-30 lg:hidden transition-opacity duration-700"
          onClick={closeMobileMenu}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative pt-16 lg:pt-0 bg-[#02060A]">
        {/* Deep Ocean Bloom */}
        <div className="absolute top-[-20%] left-[-10%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,_rgba(14,35,53,0.1)_0%,_transparent_60%)] pointer-events-none -z-10" />
        
        <div className="container mx-auto p-8 lg:p-16 max-w-7xl relative">
           <Outlet />
        </div>
      </main>
    </div>
  );
}
