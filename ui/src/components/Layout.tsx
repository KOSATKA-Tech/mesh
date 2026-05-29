import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { clsx } from 'clsx';

export default function Layout() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Map' },
    { to: '/nodes', icon: Server, label: 'Nodes' },
    { to: '/alerts', icon: Bell, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Mobile Top Bar */}
      <div className="lg:hidden absolute top-0 left-0 right-0 h-16 border-b border-border bg-card/30 backdrop-blur-md flex items-center justify-between px-4 z-50">
        <div className="flex items-center space-x-2">
          <img src="/assets/logo.png" alt="Tail" className="h-8 w-auto" />
          <span className="font-bold tracking-tighter uppercase italic text-sm">Kosatka</span>
        </div>
        <button 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Sidebar / Mobile Overlay */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-card/50 lg:bg-card/30 backdrop-blur-xl lg:backdrop-blur-md flex flex-col transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="p-6 hidden lg:flex items-center space-x-3">
          <img src="/assets/logo.png" alt="Tail" className="h-10 w-auto filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
          <span className="font-bold text-xl tracking-tighter uppercase italic">Kosatka</span>
        </div>

        <nav className="flex-1 px-4 py-20 lg:py-4 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeMobileMenu}
              className={({ isActive }) => clsx(
                "flex items-center space-x-3 px-4 py-3 rounded-xl transition-all group",
                isActive 
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" 
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-border space-y-4">
          <div className="flex items-center space-x-3 px-4">
            <div className="h-10 w-10 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center font-bold text-primary flex-shrink-0">
              {user?.username?.[0].toUpperCase() || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user?.username || 'Admin'}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email || 'System Master'}</p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full flex items-center space-x-3 px-4 py-2 text-muted-foreground hover:text-destructive transition-colors rounded-lg hover:bg-destructive/10"
          >
            <LogOut className="h-5 w-5" />
            <span className="font-medium text-sm">Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile Overlay Backdrop */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 lg:hidden"
          onClick={closeMobileMenu}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative pt-16 lg:pt-0">
        {/* Top glow decoration */}
        <div className="absolute top-0 left-1/4 w-1/2 h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent blur-sm" />
        
        <div className="container mx-auto p-4 lg:p-8 max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

