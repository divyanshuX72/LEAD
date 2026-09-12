import { useEffect } from 'react';
import { socketService } from '@/services/socket';

export function useSocket(event: string, callback: (data: any) => void) {
  useEffect(() => {
    socketService.on(event, callback);
    
    return () => {
      socketService.off(event, callback);
    };
  }, [event, callback]);
}
