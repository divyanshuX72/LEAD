import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { LeadAgentService } from '@/services/leadAgent';
import { ExportMenu } from '@/components/leads/ExportMenu';
import { WebsiteLink } from '@/components/leads/WebsiteLink';
import { ArrowLeft, Mail, Phone, MapPin, Search, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

const EmailList = ({ emails }: { emails: string[] | undefined | null }) => {
  if (!emails || emails.length === 0) return null;
  const displayEmails = emails.slice(0, 2);
  const remaining = emails.length - 2;
  return (
    <div className="flex items-start gap-1.5">
      <Mail className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0"/>
      <div className="flex flex-col gap-0.5">
        {displayEmails.map((email, i) => (
          <span key={i} className="text-slate-600 truncate max-w-[180px]" title={email}>{email}</span>
        ))}
        {remaining > 0 && <span className="text-[10px] font-medium bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full w-fit">+{remaining} more</span>}
      </div>
    </div>
  );
};

const PhoneList = ({ phones }: { phones: string[] | undefined | null }) => {
  if (!phones || phones.length === 0) return null;
  const displayPhones = phones.slice(0, 3);
  const remaining = phones.length - 3;
  return (
    <div className="flex items-start gap-1.5">
      <Phone className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0"/>
      <div className="flex flex-wrap gap-1 max-w-[200px]">
        {displayPhones.map((phone, i) => (
          <span key={i} className="bg-slate-50 border border-slate-200 text-slate-600 px-1.5 py-0.5 rounded text-[11px] whitespace-nowrap">{phone}</span>
        ))}
        {remaining > 0 && <span className="text-[10px] font-medium bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded flex items-center">+{remaining}</span>}
      </div>
    </div>
  );
};

export function BatchDetail() {
  const { batchId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  
  const [isExporting, setIsExporting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => LeadAgentService.getBatch(batchId!),
    enabled: !!batchId,
  });

  const { data: leads, isLoading: leadsLoading } = useQuery({
    queryKey: ['batch-leads', batchId],
    queryFn: () => LeadAgentService.getBatchLeads(batchId!),
    enabled: !!batchId,
  });

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (!batchId) return;
    setIsExporting(true);
    try {
      const job = await LeadAgentService.exportBatch(batchId, format);
      await LeadAgentService.downloadExport(job.id);
      toast.success("Export Started", "Your file is downloading.");
    } catch (error) {
      toast.error("Export Failed", "Could not generate the export file.");
    } finally {
      setIsExporting(false);
    }
  };

  const filteredLeads = leads?.filter(lead => 
    lead.business_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lead.emails?.some(e => e.toLowerCase().includes(searchQuery.toLowerCase())) ||
    lead.phones?.some(p => p.toLowerCase().includes(searchQuery.toLowerCase())) ||
    lead.matched_keyword?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (batchLoading || leadsLoading) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium">Batch not found</h3>
        <button onClick={() => navigate('/lead/dashboard')} className="mt-4 text-blue-600">Back to Dashboard</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button 
          onClick={() => navigate('/lead/dashboard')}
          className="p-2 rounded-full hover:bg-slate-100 text-slate-500"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{batch.name}</h1>
          <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
            <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{batch.location}</span>
            <span>•</span>
            <span>{batch.final_count} leads found</span>
            <span>•</span>
            <span className="capitalize">{batch.status}</span>
            {batch.reason && (
              <>
                <span>•</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                  {batch.reason.replace(/_/g, ' ')}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="ml-auto">
          <ExportMenu onExport={handleExport} disabled={isExporting || !leads || leads.length === 0} />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search leads in batch..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 w-full rounded-md border border-slate-200 bg-white pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50/50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-6 py-3 font-medium">Business</th>
                <th className="px-6 py-3 font-medium">Contact</th>
                <th className="px-6 py-3 font-medium">Location</th>
                <th className="px-6 py-3 font-medium">Keyword</th>
                <th className="px-6 py-3 font-medium text-right">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLeads?.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                    No leads found matching "{searchQuery}"
                  </td>
                </tr>
              ) : (
                filteredLeads?.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 align-top max-w-[250px]">
                      <div className="font-medium text-slate-900 truncate" title={lead.business_name}>{lead.business_name}</div>
                      {lead.website && <WebsiteLink url={lead.website} />}
                    </td>
                    <td className="px-6 py-4 align-top">
                      <div className="space-y-2.5 text-xs">
                        <EmailList emails={lead.emails} />
                        <PhoneList phones={lead.phones} />
                        {(!lead.emails || lead.emails.length === 0) && (!lead.phones || lead.phones.length === 0) && <span className="text-slate-400 italic">No contact info</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 align-top">
                      {lead.address ? (
                        <div className="text-xs truncate max-w-[200px]" title={lead.address}>{lead.address}</div>
                      ) : (
                        lead.city || '-'
                      )}
                    </td>
                    <td className="px-6 py-4 align-top">
                      <span className="inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
                        {lead.matched_keyword}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right align-top">
                      {lead.source_primary && (
                        <span className="capitalize text-xs font-medium text-slate-500 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                          {lead.source_primary}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
