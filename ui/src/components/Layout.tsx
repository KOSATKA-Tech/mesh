import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut, Menu, X, Sun, Moon, ChevronLeft, Maximize } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

export default function Layout() {
  const { logout, user, theme, toggleTheme } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Network' },
    { to: '/nodes', icon: Server, label: 'Nodes' },
    { to: '/alerts', icon: Bell, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground font-sans selection:bg-primary/20 antialiased transition-colors duration-500 overflow-y-auto">
      
      {/* Mobile Top Bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 border-b border-border bg-background/50 backdrop-blur-xl flex items-center justify-between px-4 z-50">
        <div className="flex items-center space-x-2">
          <img src="/admin/logo-main.png" alt="Kosatka" className={clsx("h-6 w-auto mix-blend-screen brightness-200", theme === 'light' && "invert brightness-0")} />
          <span className="font-bold tracking-[0.2em] uppercase italic text-[9px] opacity-40">Kosatka</span>
        </div>
        <div className="flex items-center space-x-1">
           <button onClick={toggleTheme} className="p-2 hover:bg-accent rounded-lg transition-colors">
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
           </button>
           <button 
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 hover:bg-accent rounded-lg transition-colors opacity-60"
            >
              {isMobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
        </div>
      </div>

      {/* SIDEBAR (Shrinked to w-64) */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-40 bg-background/95 backdrop-blur-3xl flex flex-col border-r border-border transition-all duration-500 ease-in-out lg:relative",
        isSidebarOpen ? "w-64" : "w-0 lg:w-0 -translate-x-full lg:translate-x-0 overflow-hidden",
        isMobileMenuOpen ? "translate-x-0 w-64" : ""
      )}>
        <div className="p-8 hidden lg:flex flex-col items-center space-y-6 flex-none">
          <motion.img 
            whileHover={{ scale: 1.05, filter: theme === 'dark' ? "brightness(250%)" : "brightness(50%)" }}
            src="/admin/logo-main.png" 
            alt="Kosatka" 
            className={clsx("h-16 w-auto mix-blend-screen brightness-200 drop-shadow-[0_0_30px_rgba(255,255,255,0.1)] transition-all duration-700", theme === 'light' && "invert brightness-0")} 
          />
          <div className="space-y-1">
            <div className="text-[10px] font-black uppercase tracking-[0.5em] italic opacity-50 text-center text-nowrap">
              Infrastructure
            </div>
            <div className="text-[8px] font-bold tracking-[0.3em] uppercase opacity-30 text-center text-nowrap">
              Control Plane v1.0
            </div>
          </div>
        </div>

        <nav className="flex-1 px-6 py-12 lg:py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeMobileMenu}
              className={({ isActive }) => clsx(
                "flex items-center space-x-4 px-5 py-3.5 rounded-2xl transition-all duration-500 group relative font-bold uppercase tracking-[0.2em] text-[11px] italic",
                isActive 
                  ? "bg-primary/5 text-primary shadow-[0_0_30px_rgba(255,255,255,0.01)]" 
                  : "text-foreground/30 hover:text-foreground/60 hover:bg-accent"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={clsx("h-4.5 w-4.5 transition-all duration-500 flex-none", isActive ? "text-primary scale-110" : "group-hover:scale-105")} />
                  <span className="truncate">{item.label}</span>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="absolute left-0 w-1 h-5 bg-primary/60 rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-8 border-t border-border space-y-6 bg-foreground/[0.005] flex-none">
          <div className="flex items-center justify-between px-2 mb-2">
             <span className="text-[9px] font-black uppercase tracking-widest opacity-20">Interface</span>
             <button onClick={toggleTheme} className="p-1.5 hover:bg-accent rounded-lg transition-all opacity-40 hover:opacity-100">
                {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
             </button>
          </div>

          <div className="flex items-center space-x-4 px-2">
            <div className="h-10 w-10 rounded-2xl bg-accent border border-border flex items-center justify-center font-bold opacity-50 text-xs transition-all hover:scale-105">
              {user?.username?.[0].toUpperCase() || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-black uppercase tracking-widest opacity-80 truncate">{user?.username || 'Admin'}</p>
              <p className="text-[9px] font-bold tracking-tight opacity-20 truncate lowercase italic">{user?.email || 'System Master'}</p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full flex items-center justify-center space-x-3 px-4 py-3 opacity-20 hover:opacity-100 transition-all rounded-xl border border-transparent hover:border-border hover:bg-accent"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="font-bold text-[9px] uppercase tracking-[0.3em]">Terminate</span>
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 overflow-hidden relative flex flex-col transition-all duration-500 ease-in-out">
        
        {/* DESKTOP TOP BAR (Tighter) */}
        <header className="hidden lg:flex h-16 border-b border-border bg-background/30 backdrop-blur-xl items-center justify-between px-8 flex-none z-30">
          <div className="flex items-center space-x-6">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2.5 hover:bg-accent rounded-xl transition-all border border-transparent hover:border-border shadow-lg active:scale-95"
            >
              {isSidebarOpen ? <ChevronLeft className="h-5 w-5 opacity-40" /> : <Menu className="h-5 w-5 opacity-80" />}
            </button>
            
            {!isSidebarOpen && (
              <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="flex items-center space-x-3">
                <img src="/admin/logo-main.png" alt="Kosatka" className={clsx("h-7 w-auto mix-blend-screen brightness-200", theme === 'light' && "invert brightness-0")} />
                <div className="h-5 w-px bg-border mx-1" />
                <span className="text-[9px] font-black uppercase tracking-[0.3em] opacity-30 italic">Control Plane</span>
              </motion.div>
            )}
          </div>

          <div className="flex items-center space-x-4">
            <button 
              onClick={toggleFullscreen}
              className="p-2.5 hover:bg-accent rounded-xl transition-all opacity-40 hover:opacity-100"
              title="Toggle Fullscreen"
            >
              <Maximize className="h-4.5 w-4.5" />
            </button>
            {!isSidebarOpen && (
              <button onClick={toggleTheme} className="p-2.5 hover:bg-accent rounded-xl transition-all opacity-40 hover:opacity-100">
                {theme === 'dark' ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
              </button>
            )}
            <div className="text-right hidden sm:block">
               <p className="text-[10px] font-black uppercase tracking-widest opacity-80">{user?.username || 'Admin'}</p>
               <p className="text-[8px] font-bold uppercase tracking-widest opacity-20 italic">Master_Entity</p>
            </div>
          </div>
        </header>

        {/* CONTENT */}
        <div className="flex-1 relative min-h-0 pt-14 lg:pt-0 bg-background overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,_var(--accent)_0%,_transparent_60%)] pointer-events-none -z-10 opacity-30" />
          
          <div className={clsx(
             "h-full w-full p-4 lg:p-8 relative transition-all duration-500 overflow-y-auto",
             isSidebarOpen ? "scale-100" : "scale-[1.002]"
          )}>
             <Outlet />
          </div>
        </div>
      </main>

      {/* Mobile Overlay Backdrop */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-xl z-30 lg:hidden"
            onClick={closeMobileMenu}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
