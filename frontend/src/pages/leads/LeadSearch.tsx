import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { LeadAgentService } from '@/services/leadAgent';
import { useLeadStore } from '@/store/leadStore';
import { Card, CardHeader, CardTitle, CardContent, Input, Button } from '@/components/ui';
import { KeywordInput } from '@/components/leads/KeywordInput';
import { MapPin, Sparkles, AlertCircle, Target } from 'lucide-react';

export function LeadSearch() {
  const navigate = useNavigate();
  const { activeSearch, setActiveSearch } = useLeadStore();
  
  const [keywords, setKeywords] = useState<string[]>([]);
  const [location, setLocation] = useState('');
  const [maxResults, setMaxResults] = useState(50);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState('');

  // Clear search on mount if completed
  useEffect(() => {
    if (activeSearch?.status === 'completed' || activeSearch?.status === 'failed') {
      setActiveSearch(null);
    }
  }, []);

  const handleDiscover = async () => {
    if (keywords.length === 0) {
      setError('Please add at least one keyword.');
      return;
    }
    if (!location.trim()) {
      setError('Please provide a target location.');
      return;
    }

    setIsStarting(true);
    setError('');

    try {
      const result = await LeadAgentService.startSearch(keywords, location, maxResults);

      setActiveSearch({
        batch_id: result.batch_id,
        status: 'running',
        current_keyword: keywords[0],
        keywords_completed: 0,
        keywords_total: keywords.length,
        leads_found: 0,
        leads_target: maxResults,
        message: 'Initializing search...'
      });

    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.error;
      const errorMessage = typeof detail === 'string' ? detail : 
                          (Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : 
                           'Failed to start discovery session.');
      setError(errorMessage);
    } finally {
      setIsStarting(false);
    }
  };

  const isRunning = activeSearch?.status === 'running';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Lead Search Engine</h1>
        <p className="text-slate-500 mt-1">
          Enter multiple keywords to find highly targeted B2B leads in any location.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Target className="h-5 w-5 text-blue-600" />
                Search Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {error && (
                <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-md border border-red-100">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Keywords <span className="text-red-500">*</span></label>
                <KeywordInput 
                  value={keywords} 
                  onChange={setKeywords} 
                  placeholder="e.g. Dentist, Dental Clinic"
                  disabled={isRunning}
                />
                <p className="text-xs text-slate-500">
                  Press Enter or comma to add multiple keywords. The engine will search exactly for what you enter.
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Target Location <span className="text-red-500">*</span></label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input 
                    placeholder="e.g. Mumbai, India"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="pl-9"
                    disabled={isRunning}
                  />
                </div>
                <p className="text-xs text-slate-500">City, state, or country name.</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Lead Target</label>
                <select 
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  disabled={isRunning}
                >
                  <option value={10}>Quick Test (10 leads)</option>
                  <option value={50}>Standard (50 leads)</option>
                  <option value={100}>Deep Scan (100 leads)</option>
                  <option value={500}>Maximum (500 leads)</option>
                </select>
                <p className="text-xs text-slate-500">The engine will stop once this target is reached.</p>
              </div>

              {!isRunning ? (
                <Button 
                  className="w-full mt-2 h-11 text-base font-medium" 
                  size="lg"
                  onClick={handleDiscover}
                  disabled={isStarting}
                >
                  {isStarting ? 'Initializing...' : 'Start Search'}
                </Button>
              ) : (
                <Button 
                  variant="destructive"
                  className="w-full mt-2 h-11 text-base font-medium" 
                  size="lg"
                  onClick={async () => {
                    if (!activeSearch) return;
                    try {
                      // Update UI immediately
                      setActiveSearch({ ...activeSearch, status: 'stopped', message: 'Stopping search...' });
                      await LeadAgentService.stopSearch(activeSearch.batch_id);
                    } catch (e) {
                      console.error('Failed to stop search', e);
                      // Revert if failed
                      setActiveSearch({ ...activeSearch, status: 'running' });
                    }
                  }}
                >
                  Stop
                </Button>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {activeSearch ? (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full min-h-[400px]">
              <div className="p-6 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <h3 className="font-semibold text-slate-800">Search Progress</h3>
                <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                  activeSearch.status === 'completed' ? 'bg-green-100 text-green-800' :
                  activeSearch.status === 'partial' ? 'bg-yellow-100 text-yellow-800' :
                  activeSearch.status === 'failed' ? 'bg-red-100 text-red-800' :
                  activeSearch.status === 'stopped' ? 'bg-orange-100 text-orange-800' :
                  'bg-blue-100 text-blue-800 animate-pulse'
                }`}>
                  {activeSearch.status.toUpperCase()}
                </span>
              </div>
              
              <div className="p-8 flex-1 flex flex-col justify-center max-w-md mx-auto w-full">
                <div className="text-center mb-8">
                  <div className="text-5xl font-bold text-blue-600 mb-2">
                    {activeSearch.leads_found}
                  </div>
                  <div className="text-sm font-medium text-slate-500 uppercase tracking-wider">
                    Leads Discovered
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-medium text-slate-700">Target Progress</span>
                      <span className="text-slate-500">{activeSearch.leads_found} / {activeSearch.leads_target}</span>
                    </div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-500 transition-all duration-500 ease-out"
                        style={{ width: `${Math.min(100, (activeSearch.leads_found / activeSearch.leads_target) * 100)}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm mb-6 border-t border-slate-100 pt-6 mt-4">
                    <div>
                      <p className="text-slate-500 font-medium">Requested</p>
                      <p className="font-bold text-slate-800">{activeSearch.leads_target}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-medium">Found</p>
                      <p className="font-bold text-slate-800">{activeSearch.leads_found}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-medium">Duplicates</p>
                      <p className="font-bold text-slate-800">{activeSearch.duplicates || 0}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-medium">Scanned</p>
                      <p className="font-bold text-slate-800">{activeSearch.scanned || 0}</p>
                    </div>
                  </div>

                  {activeSearch.message && (
                    <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg text-sm text-slate-600 border border-slate-100">
                      {isRunning && (
                        <div className="h-4 w-4 shrink-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                      )}
                      {!isRunning && (
                        <div className="h-2 w-2 rounded-full bg-slate-400"></div>
                      )}
                      <p className="truncate flex-1" title={activeSearch.message}>{activeSearch.message}</p>
                      {isRunning && (activeSearch.retry_round || 0) > 0 && (
                        <span className="shrink-0 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                          Retry {activeSearch.retry_round}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {activeSearch.status === 'partial' && activeSearch.reason !== 'timeout' && (
                  <div className="mt-4 space-y-4">
                    <div className="p-4 bg-yellow-50 text-yellow-800 text-sm rounded-lg border border-yellow-100 flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 shrink-0 text-yellow-600" />
                      <div>
                        <p className="font-semibold mb-1">
                          {activeSearch.reason === 'retries_exhausted'
                            ? `Exhausted all keyword variations. Found ${activeSearch.leads_found} unique leads.`
                            : 'Could not find more leads. Showing best available results.'}
                        </p>
                        {(activeSearch.retry_round || 0) > 0 && (
                          <p className="text-yellow-700 mb-1">Tried {activeSearch.retry_round} round(s) of keyword expansion.</p>
                        )}
                        <p className="text-yellow-700">To get more leads, try:</p>
                        <ul className="list-disc pl-5 mt-1 space-y-1">
                          <li>adding more specific keywords manually</li>
                          <li>broader location (e.g. state or country)</li>
                          <li>alternative industry terms</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {activeSearch.status === 'partial' && activeSearch.reason === 'timeout' && (
                  <div className="mt-4 space-y-4">
                    <div className="p-4 bg-yellow-50 text-yellow-800 text-sm rounded-lg border border-yellow-100 flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 shrink-0 text-yellow-600" />
                      <div>
                        <p className="font-semibold mb-1">Search stopped due to timeout (10 sec). Showing best results.</p>
                      </div>
                    </div>
                  </div>
                )}

                {activeSearch.status === 'stopped' && (
                  <div className="mt-4 space-y-4">
                    <div className="p-4 bg-orange-50 text-orange-800 text-sm rounded-lg border border-orange-100 flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 shrink-0 text-orange-600" />
                      <div>
                        <p className="font-semibold mb-1">Search stopped manually. Showing collected leads.</p>
                      </div>
                    </div>
                  </div>
                )}

                {(activeSearch.status === 'completed' || activeSearch.status === 'partial' || activeSearch.status === 'stopped') && (
                  <div className="mt-8 flex justify-center">
                    <Button 
                      onClick={() => navigate(`/lead/dashboard/${activeSearch.batch_id}`)}
                      className="w-full sm:w-auto"
                    >
                      View Results
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50 text-center p-8">
              <div className="h-16 w-16 rounded-full bg-blue-50 flex items-center justify-center mb-4 ring-8 ring-white shadow-sm">
                <Sparkles className="h-7 w-7 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Ready to discover leads</h3>
              <p className="text-slate-500 max-w-md mx-auto">
                Configure your search parameters on the left. The agent will scan multiple search engines and directories to build a deduplicated list of business leads.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
