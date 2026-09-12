import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { LeadAgentService } from '@/services/leadAgent';
import { BatchCard } from '@/components/leads/BatchCard';
import { ExportMenu } from '@/components/leads/ExportMenu';
import { Card, CardContent } from '@/components/ui';
import { Users, Folder, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

export function LeadDashboard() {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  
  const [selectedBatches, setSelectedBatches] = useState<string[]>([]);
  const [isExporting, setIsExporting] = useState(false);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => LeadAgentService.getStats(),
    refetchInterval: 3000,
  });

  const { data: batches, isLoading: batchesLoading } = useQuery({
    queryKey: ['lead-batches'],
    queryFn: () => LeadAgentService.getBatches(100),
    refetchInterval: 3000,
  });

  const toggleBatch = (batchId: string) => {
    setSelectedBatches(prev => 
      prev.includes(batchId) ? prev.filter(id => id !== batchId) : [...prev, batchId]
    );
  };

  const selectAll = () => {
    if (!batches) return;
    if (selectedBatches.length === batches.length) {
      setSelectedBatches([]);
    } else {
      setSelectedBatches(batches.map(b => b.id));
    }
  };

  const handleExport = async (format: 'csv' | 'xlsx', type: 'selected' | 'all') => {
    setIsExporting(true);
    try {
      let job;
      if (type === 'selected' && selectedBatches.length > 0) {
        job = await LeadAgentService.exportSelectedBatches(selectedBatches, format);
      } else {
        job = await LeadAgentService.exportAll(format, false); // export all, don't restrict to unique
      }
      
      // Auto download
      await LeadAgentService.downloadExport(job.id);
      
      toast.success("Export Started", `Your ${format.toUpperCase()} file is downloading.`);
    } catch (error) {
      toast.error("Export Failed", "Could not generate the export file.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteBatch = async (batchId: string) => {
    if (!window.confirm("Are you sure you want to delete this search? All leads will be permanently deleted.")) return;
    try {
      await LeadAgentService.deleteBatch(batchId);
      toast.success("Deleted", "Search batch deleted successfully.");
      queryClient.invalidateQueries({ queryKey: ['lead-batches'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      setSelectedBatches(prev => prev.filter(id => id !== batchId));
    } catch (error) {
      toast.error("Delete Failed", "Could not delete the batch.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Lead Dashboard</h1>
          <p className="text-slate-500 mt-1">Manage your lead discovery batches and export data.</p>
        </div>
        <div className="flex items-center gap-3">
          {selectedBatches.length > 0 ? (
            <ExportMenu 
              label={`Export Selected (${selectedBatches.length})`} 
              onExport={(fmt) => handleExport(fmt, 'selected')} 
              disabled={isExporting}
            />
          ) : (
            <ExportMenu 
              label="Export All Leads" 
              variant="outline"
              onExport={(fmt) => handleExport(fmt, 'all')} 
              disabled={isExporting || (stats?.total_leads === 0)}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
              <Users className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Total Leads</p>
              <h4 className="text-2xl font-bold text-slate-900">
                {statsLoading ? <Loader2 className="h-5 w-5 animate-spin text-slate-300" /> : stats?.total_leads.toLocaleString()}
              </h4>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6 flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-indigo-50 flex items-center justify-center shrink-0">
              <Folder className="h-6 w-6 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-500">Search Batches</p>
              <h4 className="text-2xl font-bold text-slate-900">
                {statsLoading ? <Loader2 className="h-5 w-5 animate-spin text-slate-300" /> : stats?.total_batches.toLocaleString()}
              </h4>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-3">
            <input 
              type="checkbox" 
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600 cursor-pointer"
              checked={batches && batches.length > 0 && selectedBatches.length === batches.length}
              onChange={selectAll}
            />
            <h3 className="font-semibold text-slate-800">Search Batches</h3>
          </div>
          <span className="text-sm text-slate-500">
            {batches?.length || 0} total
          </span>
        </div>
        
        <div className="p-6 bg-slate-50/30 min-h-[400px]">
          {batchesLoading ? (
            <div className="flex justify-center items-center h-40">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : batches && batches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {batches.map(batch => (
                <BatchCard 
                  key={batch.id} 
                  batch={batch} 
                  onClick={() => navigate(`/lead/dashboard/${batch.id}`)}
                  isSelected={selectedBatches.includes(batch.id)}
                  onToggleSelect={() => toggleBatch(batch.id)}
                  onDelete={() => handleDeleteBatch(batch.id)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <Folder className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900">No batches yet</h3>
              <p className="mt-1 text-slate-500">Start a lead search to create your first batch.</p>
              <button 
                onClick={() => navigate('/lead/search')}
                className="mt-4 text-blue-600 hover:text-blue-700 font-medium text-sm"
              >
                Go to Search Engine →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
