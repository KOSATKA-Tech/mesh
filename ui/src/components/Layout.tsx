import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut, Menu, X, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

export default function Layout() {
  const { logout, user, theme, toggleTheme } = useAuth();
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
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-primary/20 antialiased transition-colors duration-500">
      {/* Mobile Top Bar */}
      <div className="lg:hidden absolute top-0 left-0 right-0 h-16 border-b border-border bg-background/50 backdrop-blur-xl flex items-center justify-between px-6 z-50">
        <div className="flex items-center space-x-3">
          <img src="/admin/logo-main.png" alt="Kosatka" className={clsx("h-8 w-auto mix-blend-screen brightness-200", theme === 'light' && "invert brightness-0")} />
          <span className="font-bold tracking-[0.3em] uppercase italic text-[10px] opacity-40">Kosatka</span>
        </div>
        <div className="flex items-center space-x-2">
           <button onClick={toggleTheme} className="p-2 hover:bg-accent rounded-lg transition-colors">
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
           </button>
           <button 
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 hover:bg-accent rounded-lg transition-colors opacity-60"
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
        </div>
      </div>

      {/* Sidebar / Mobile Overlay */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-40 w-72 border-r border-border bg-background/90 backdrop-blur-3xl flex flex-col transform transition-transform duration-500 ease-in-out lg:relative lg:translate-x-0 lg:bg-transparent lg:backdrop-blur-none",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="p-12 hidden lg:flex flex-col items-center space-y-8">
          <motion.img 
            whileHover={{ scale: 1.05, filter: theme === 'dark' ? "brightness(250%)" : "brightness(50%)" }}
            src="/admin/logo-main.png" 
            alt="Kosatka" 
            className={clsx("h-24 w-auto mix-blend-screen brightness-200 drop-shadow-[0_0_40px_rgba(255,255,255,0.1)] transition-all duration-700", theme === 'light' && "invert brightness-0")} 
          />
          <div className="space-y-2">
            <div className="text-[12px] font-black uppercase tracking-[0.6em] italic opacity-50 text-center">
              Infrastructure
            </div>
            <div className="text-[10px] font-bold tracking-[0.4em] uppercase opacity-30 text-center">
              Control Plane v1.0
            </div>
          </div>
        </div>

        <nav className="flex-1 px-8 py-20 lg:py-6 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeMobileMenu}
              className={({ isActive }) => clsx(
                "flex items-center space-x-6 px-8 py-5 rounded-[24px] transition-all duration-500 group relative font-bold uppercase tracking-[0.25em] text-[13px] italic",
                isActive 
                  ? "bg-primary/10 text-primary shadow-[0_0_40px_rgba(255,255,255,0.02)]" 
                  : "text-foreground/30 hover:text-foreground/60 hover:bg-accent"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={clsx("h-6 w-6 transition-all duration-500", isActive ? "text-primary scale-110" : "group-hover:scale-105")} />
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="absolute left-0 w-1.5 h-6 bg-primary/60 rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-10 border-t border-border space-y-8 bg-foreground/[0.01]">
          <div className="flex items-center justify-between px-2 mb-4">
             <span className="text-[10px] font-black uppercase tracking-widest opacity-20">Interface Theme</span>
             <button onClick={toggleTheme} className="p-2 hover:bg-accent rounded-xl transition-all">
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
             </button>
          </div>

          <div className="flex items-center space-x-5 px-2">
            <div className="h-12 w-12 rounded-3xl bg-accent border border-border flex items-center justify-center font-bold opacity-50 text-sm transition-all hover:scale-105 shadow-xl">
              {user?.username?.[0].toUpperCase() || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-black uppercase tracking-widest opacity-80 truncate">{user?.username || 'Admin'}</p>
              <p className="text-[10px] font-bold tracking-tight opacity-20 truncate lowercase italic">{user?.email || 'System Master'}</p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full flex items-center justify-center space-x-4 px-6 py-4 opacity-20 hover:opacity-100 transition-all rounded-[20px] border border-transparent hover:border-border hover:bg-accent shadow-inner"
          >
            <LogOut className="h-4 w-4" />
            <span className="font-bold text-[11px] uppercase tracking-[0.4em]">Terminate</span>
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
      <main className="flex-1 overflow-auto relative pt-16 lg:pt-0 bg-background">
        <div className="absolute top-[-20%] left-[-10%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,_var(--accent)_0%,_transparent_60%)] pointer-events-none -z-10 opacity-30" />
        
        <div className="container mx-auto p-8 lg:p-16 max-w-7xl relative min-h-full">
           <Outlet />
        </div>
      </main>
    </div>
  );
}
