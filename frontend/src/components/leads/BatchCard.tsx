import type { LeadBatch } from '@/types/lead';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { MapPin, Calendar, Trash2 } from 'lucide-react';

interface BatchCardProps {
  batch: LeadBatch;
  onClick: () => void;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onDelete?: (e: React.MouseEvent) => void;
}

export function BatchCard({ batch, onClick, isSelected, onToggleSelect, onDelete }: BatchCardProps) {
  let displayStatus = batch.status;
  if (displayStatus === 'pending' && batch.final_count > 0) {
    displayStatus = 'running';
  }
  
  const isCompleted = displayStatus === 'completed';
  const isRunning = displayStatus === 'running';

  return (
    <Card 
      className={`cursor-pointer transition-colors hover:border-blue-300 ${isSelected ? 'border-blue-500 ring-1 ring-blue-500' : ''}`}
      onClick={(e) => {
        // Only trigger click if we aren't clicking the checkbox itself
        if ((e.target as HTMLElement).tagName !== 'INPUT') {
          onClick();
        }
      }}
    >
      <CardHeader className="pb-3 flex flex-row justify-between items-start">
        <div className="flex gap-3">
          {onToggleSelect && (
            <input 
              type="checkbox" 
              className="mt-1.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600 cursor-pointer"
              checked={isSelected}
              onChange={onToggleSelect}
              onClick={(e) => e.stopPropagation()}
            />
          )}
          <div>
            <CardTitle className="text-lg font-semibold text-slate-900 leading-tight">
              {batch.name}
            </CardTitle>
            <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {batch.location}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(batch.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className={`px-2.5 py-1 text-xs font-medium rounded-full ${
            isCompleted ? 'bg-green-100 text-green-800' : 
            isRunning ? 'bg-blue-100 text-blue-800' : 
            displayStatus === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-yellow-100 text-yellow-800'
          }`}>
            {displayStatus.charAt(0).toUpperCase() + displayStatus.slice(1)}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {batch.reason && (
              <span className="text-[10px] text-slate-400 capitalize px-1">
                {batch.reason.replace(/_/g, ' ')}
              </span>
            )}
            {onDelete && (
              <button 
                onClick={(e) => { e.stopPropagation(); onDelete(e); }}
                className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                title="Delete Batch"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 border-t border-slate-100 pt-3">
          <div>
            <p className="text-xs text-slate-500">Requested</p>
            <p className="font-semibold text-slate-900">{batch.requested_count}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Found</p>
            <p className="font-semibold text-slate-900">{batch.final_count}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Duplicates</p>
            <p className="font-semibold text-slate-500">{batch.duplicate_count}</p>
          </div>
        </div>
        {batch.keywords && batch.keywords.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
            {batch.keywords.slice(0, 3).map((kw, i) => (
              <span key={i} className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                {kw}
              </span>
            ))}
            {batch.keywords.length > 3 && (
              <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                +{batch.keywords.length - 3} more
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
