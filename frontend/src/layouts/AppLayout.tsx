import { Outlet } from 'react-router';
import { Sidebar } from '@/components/Sidebar';
import { useEffect } from 'react';
import { useLeadStore } from '@/store/leadStore';
import { socketService } from '@/services/socket';
import { useQueryClient } from '@tanstack/react-query';
import { ToastContainer } from '@/components/ui/Toast';
import { Search as SearchIcon, User, LogOut } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export function AppLayout() {
  const { updateSearchProgress, setActiveSearch } = useLeadStore();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    socketService.connect();
    
    // For Lead Agent, we join a global room instead of workspace-specific
    socketService.joinWorkspace('lead_agent');

    // Register real-time event listeners for the Lead Agent
    const unsubs = [
      socketService.onDiscoveryEvent('search_started', () => {
        // Search initiated
      }),
      socketService.onDiscoveryEvent('search_progress', (data) => {
        updateSearchProgress({
          status: 'running',
          current_keyword: data.current_keyword,
          leads_found: data.leads_found,
          leads_target: data.leads_target,
          duplicates: data.duplicates,
          scanned: data.scanned,
          message: data.message,
          retry_round: data.retry_round || 0,
        });
      }),
      socketService.onDiscoveryEvent('lead_discovered', (data) => {
        updateSearchProgress({
          leads_found: data.leads_found,
        });
        // Invalidate leads query if viewing batch
        queryClient.invalidateQueries({ queryKey: ['batch-leads', data.batch_id] });
      }),
      socketService.onDiscoveryEvent('search_completed', (data) => {
        updateSearchProgress({ 
          status: data.status, // completed or partial
          leads_found: data.final_count,
          duplicates: data.duplicates,
          scanned: data.raw_results,
          reason: data.reason,
          retry_round: data.retry_rounds || 0,
        });
        queryClient.invalidateQueries({ queryKey: ['lead-batches'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      }),
      socketService.onDiscoveryEvent('search_failed', (data) => {
        updateSearchProgress({ 
          status: 'failed', 
          message: data.error 
        });
      })
    ];

    return () => {
      unsubs.forEach(unsub => unsub());
      socketService.disconnect();
    };
  }, [updateSearchProgress, setActiveSearch, queryClient]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
          <div className="flex flex-1 items-center max-w-md">
            <div className="relative w-full hidden">
              {/* Optional global search can go here later */}
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search leads..." 
                className="h-9 w-full rounded-md border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="group relative">
              <button className="flex items-center space-x-3 rounded-full focus:outline-none transition-opacity hover:opacity-80">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-white shadow-sm ring-2 ring-slate-100">
                  <User className="h-4 w-4" />
                </div>
                <div className="hidden sm:flex flex-col items-start">
                  <span className="text-sm font-semibold text-slate-800 leading-none mb-1">{user?.company_name || 'My Company'}</span>
                  <span className="text-[11px] text-slate-500 leading-none">{user?.email || 'User'}</span>
                </div>
              </button>
              <div className="absolute right-0 mt-3 w-56 origin-top-right rounded-xl bg-white p-2 shadow-xl ring-1 ring-slate-900/5 focus:outline-none hidden group-hover:block z-50">
                <div className="px-3 py-2 border-b border-slate-100 mb-1">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Account</p>
                </div>
                <button 
                  onClick={() => useAuthStore.getState().logout()} 
                  className="w-full flex items-center space-x-2 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6 relative">
          <ToastContainer />
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
