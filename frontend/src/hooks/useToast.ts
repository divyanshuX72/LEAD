import { useToastStore, type ToastType, type Toast } from '@/store/toastStore';

export function useToast() {
  const addToast = useToastStore((state) => state.addToast);

  const showToast = (type: ToastType, title: string, message?: string, duration?: number) => {
    addToast({ type, title, message, duration });
  };

  return {
    success: (title: string, message?: string, duration?: number) => showToast('success', title, message, duration),
    error: (title: string, message?: string, duration?: number) => showToast('error', title, message, duration),
    warning: (title: string, message?: string, duration?: number) => showToast('warning', title, message, duration),
    info: (title: string, message?: string, duration?: number) => showToast('info', title, message, duration),
    custom: (toast: Omit<Toast, 'id'>) => addToast(toast),
  };
}
