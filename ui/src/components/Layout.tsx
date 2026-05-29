import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Server, Settings, Bell, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { clsx } from 'clsx';

export default function Layout() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Map' },
    { to: '/nodes', icon: Server, label: 'Nodes' },
    { to: '/alerts', icon: Bell, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card/30 backdrop-blur-md flex flex-col">
        <div className="p-6 flex items-center space-x-3">
          <img src="/assets/logo.png" alt="Tail" className="h-10 w-auto filter drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]" />
          <span className="font-bold text-xl tracking-tighter uppercase italic">Kosatka</span>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
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
            <div className="h-10 w-10 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center font-bold text-primary">
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

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative">
        {/* Top glow decoration */}
        <div className="absolute top-0 left-1/4 w-1/2 h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent blur-sm" />
        
        <div className="container mx-auto p-8 max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
