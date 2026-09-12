import { useState, useRef, useCallback } from 'react';
import { cn } from '@/utils/utils';
import { Upload, FileText } from 'lucide-react';

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  className?: string;
  disabled?: boolean;
}

export function DropZone({
  onFiles,
  accept,
  multiple = true,
  maxSizeMB = 50,
  className,
  disabled = false,
}: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || disabled) return;
      const files = Array.from(fileList).filter(
        (f) => f.size <= maxSizeMB * 1024 * 1024
      );
      if (files.length > 0) onFiles(files);
    },
    [onFiles, maxSizeMB, disabled]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!disabled) setIsDragOver(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => !disabled && inputRef.current?.click()}
      className={cn(
        'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all cursor-pointer',
        isDragOver
          ? 'border-blue-400 bg-blue-50/50 scale-[1.01]'
          : 'border-slate-300 bg-slate-50/50 hover:border-slate-400 hover:bg-slate-100/50',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(e) => handleFiles(e.target.files)}
        className="hidden"
        disabled={disabled}
      />
      <div
        className={cn(
          'mb-3 flex h-12 w-12 items-center justify-center rounded-full transition-colors',
          isDragOver ? 'bg-blue-100' : 'bg-slate-100'
        )}
      >
        {isDragOver ? (
          <FileText className="h-6 w-6 text-blue-500" />
        ) : (
          <Upload className="h-6 w-6 text-slate-400" />
        )}
      </div>
      <p className="text-sm font-medium text-slate-700">
        {isDragOver ? 'Drop files here' : 'Drag & drop files, or click to browse'}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        PDF, DOCX, TXT, CSV, XLSX, PPTX, Images • Max {maxSizeMB}MB per file
      </p>
    </div>
  );
}
