import { NavLink, useNavigate, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardList,
  Package,
  LogOut,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react';
import { clearToken, getCurrentUser } from '@/lib/auth';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { to: '/dashboard',   label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/inspections', label: 'Inspections', icon: ClipboardList },
  { to: '/products',    label: 'Products',    icon: Package },
];

export function AppShell() {
  const navigate = useNavigate();
  const user = getCurrentUser();

  const handleLogout = () => {
    clearToken();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-slate-200 bg-white shadow-sm">
        {/* Logo */}
        <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
          <ShieldCheck className="h-6 w-6 text-blue-700 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold tracking-tight text-slate-900">INSPECTRA</p>
            <p className="text-[10px] text-slate-400 leading-tight">Legal Metrology</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={cn('h-4 w-4 flex-shrink-0', isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600')} />
                  <span className="flex-1">{label}</span>
                  {isActive && <ChevronRight className="h-3 w-3 text-blue-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-slate-100 p-3">
          <div className="flex items-center gap-3 rounded-md px-2 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-700 text-xs font-bold text-white flex-shrink-0">
              {user?.name?.charAt(0).toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-xs font-semibold text-slate-900">{user?.name ?? 'User'}</p>
              <p className="truncate text-[10px] text-slate-400">{user?.role}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-red-500 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
