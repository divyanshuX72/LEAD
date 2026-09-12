import { useState, useRef, useEffect } from 'react';
import { Download, FileSpreadsheet, FileText, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui';

interface ExportMenuProps {
  onExport: (format: 'csv' | 'xlsx') => void;
  disabled?: boolean;
  label?: string;
  variant?: 'default' | 'outline' | 'secondary' | 'ghost';
}

export function ExportMenu({ onExport, disabled, label = "Export", variant = "default" }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <Button 
        variant={variant}
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2"
      >
        <Download className="h-4 w-4" />
        {label}
        <ChevronDown className="h-4 w-4" />
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 z-50">
          <button
            onClick={() => { onExport('csv'); setIsOpen(false); }}
            className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            <FileText className="h-4 w-4 text-blue-600" />
            Export as CSV
          </button>
          <button
            onClick={() => { onExport('xlsx'); setIsOpen(false); }}
            className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            <FileSpreadsheet className="h-4 w-4 text-green-600" />
            Export as Excel
          </button>
        </div>
      )}
    </div>
  );
}
