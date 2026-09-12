import { Link, useLocation } from 'react-router';
import { cn } from '@/utils/utils';
import { 
  Search, 
  FolderOpen,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useStore } from '@/store';

const navItems = [
  {
    title: 'Lead Search',
    href: '/lead/search',
    icon: Search,
  },
  {
    title: 'Dashboard',
    href: '/lead/dashboard',
    icon: FolderOpen,
  }
];

export function Sidebar() {
  const location = useLocation();
  const { isSidebarOpen, toggleSidebar } = useStore();

  return (
    <aside
      className={cn(
        "relative flex h-full flex-col border-r border-slate-200 bg-white transition-all duration-300",
        isSidebarOpen ? "w-64" : "w-16"
      )}
    >
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-100">
        <div className={cn(
          "flex items-center gap-2 overflow-hidden transition-opacity duration-300",
          !isSidebarOpen && "opacity-0 w-0"
        )}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold shrink-0">
            LA
          </div>
          <span className="font-semibold text-slate-900 truncate">Lead Agent</span>
        </div>
        <button
          onClick={toggleSidebar}
          className="absolute -right-3 top-5 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900 shadow-sm"
        >
          {isSidebarOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.href);
          
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900",
                !isSidebarOpen && "justify-center px-0"
              )}
              title={!isSidebarOpen ? item.title : undefined}
            >
              <item.icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-colors",
                  isActive ? "text-blue-700" : "text-slate-400 group-hover:text-slate-600"
                )}
              />
              {isSidebarOpen && (
                <span className="truncate">{item.title}</span>
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
