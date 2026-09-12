import { Modal } from './Modal';
import { Button } from './Button';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'default';
  isLoading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
  isLoading = false,
}: ConfirmDialogProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md">
      <div className="flex flex-col items-center text-center">
        <div
          className={`mb-4 flex h-12 w-12 items-center justify-center rounded-full ${
            variant === 'danger'
              ? 'bg-red-100'
              : variant === 'warning'
                ? 'bg-amber-100'
                : 'bg-slate-100'
          }`}
        >
          <AlertTriangle
            className={`h-6 w-6 ${
              variant === 'danger'
                ? 'text-red-600'
                : variant === 'warning'
                  ? 'text-amber-600'
                  : 'text-slate-600'
            }`}
          />
        </div>
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <p className="mt-2 text-sm text-slate-500">{message}</p>
      </div>
      <div className="mt-6 flex gap-3">
        <Button variant="outline" className="flex-1" onClick={onClose} disabled={isLoading}>
          {cancelText}
        </Button>
        <Button
          variant={variant === 'danger' ? 'destructive' : 'default'}
          className="flex-1"
          onClick={onConfirm}
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : confirmText}
        </Button>
      </div>
    </Modal>
  );
}
