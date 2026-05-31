import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut, Menu, X, Sun, Moon, ChevronLeft } from 'lucide-react';
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

      {/* SIDEBAR */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-40 bg-background/95 backdrop-blur-3xl flex flex-col border-r border-border transition-all duration-700 ease-in-out lg:relative",
        isSidebarOpen ? "w-72" : "w-0 lg:w-0 -translate-x-full lg:translate-x-0 overflow-hidden",
        isMobileMenuOpen ? "translate-x-0 w-72" : ""
      )}>
        <div className="p-12 hidden lg:flex flex-col items-center space-y-8 flex-none">
          <motion.img 
            whileHover={{ scale: 1.05, filter: theme === 'dark' ? "brightness(250%)" : "brightness(50%)" }}
            src="/admin/logo-main.png" 
            alt="Kosatka" 
            className={clsx("h-24 w-auto mix-blend-screen brightness-200 drop-shadow-[0_0_40px_rgba(255,255,255,0.1)] transition-all duration-700", theme === 'light' && "invert brightness-0")} 
          />
          <div className="space-y-2">
            <div className="text-[12px] font-black uppercase tracking-[0.6em] italic opacity-50 text-center text-nowrap">
              Infrastructure
            </div>
            <div className="text-[10px] font-bold tracking-[0.4em] uppercase opacity-30 text-center text-nowrap">
              Control Plane v1.0
            </div>
          </div>
        </div>

        <nav className="flex-1 px-8 py-20 lg:py-6 space-y-2 overflow-y-auto">
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
                  <item.icon className={clsx("h-6 w-6 transition-all duration-500 flex-none", isActive ? "text-primary scale-110" : "group-hover:scale-105")} />
                  <span className="truncate">{item.label}</span>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="absolute left-0 w-1.5 h-6 bg-primary/60 rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-10 border-t border-border space-y-8 bg-foreground/[0.01] flex-none">
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

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 overflow-auto relative flex flex-col transition-all duration-700 ease-in-out">
        
        {/* DESKTOP TOP BAR (Only visible when sidebar is closed or for small layout fixes) */}
        <header className="hidden lg:flex h-20 border-b border-border bg-background/50 backdrop-blur-xl items-center justify-between px-10 flex-none z-30">
          <div className="flex items-center space-x-8">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-3 hover:bg-accent rounded-2xl transition-all border border-border/0 hover:border-border shadow-2xl active:scale-95"
            >
              {isSidebarOpen ? <ChevronLeft className="h-6 w-6 opacity-40" /> : <Menu className="h-6 w-6 opacity-80" />}
            </button>
            
            {!isSidebarOpen && (
              <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="flex items-center space-x-4">
                <img src="/admin/logo-main.png" alt="Kosatka" className={clsx("h-10 w-auto mix-blend-screen brightness-200", theme === 'light' && "invert brightness-0")} />
                <div className="h-6 w-px bg-border mx-2" />
                <span className="text-[10px] font-black uppercase tracking-[0.4em] opacity-30">Control Plane</span>
              </motion.div>
            )}
          </div>

          <div className="flex items-center space-x-6">
            {!isSidebarOpen && (
              <button onClick={toggleTheme} className="p-3 hover:bg-accent rounded-2xl transition-all opacity-40 hover:opacity-100">
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            )}
            <div className="text-right">
               <p className="text-[11px] font-black uppercase tracking-widest opacity-80">{user?.username || 'Admin'}</p>
               <p className="text-[8px] font-bold uppercase tracking-widest opacity-20 italic">Master_Entity</p>
            </div>
          </div>
        </header>

        {/* CONTENT */}
        <div className="flex-1 relative min-h-0 pt-16 lg:pt-0 bg-background overflow-y-auto overflow-x-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[140%] h-[140%] bg-[radial-gradient(circle_at_center,_var(--accent)_0%,_transparent_60%)] pointer-events-none -z-10 opacity-30" />
          
          <div className={clsx(
             "container mx-auto p-8 lg:p-12 max-w-[1600px] relative min-h-full transition-all duration-700",
             isSidebarOpen ? "opacity-100 scale-100" : "opacity-100 scale-[1.002]"
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
