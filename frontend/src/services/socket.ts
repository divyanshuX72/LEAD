import { io, Socket } from 'socket.io-client';

const SOCKET_URL = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8000';

class SocketService {
  private socket: Socket | null = null;
  private workspaceId: string | null = null;

  connect() {
    if (this.socket?.connected) return;
    
    this.socket = io(SOCKET_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });

    this.socket.on('connect', () => {
      console.log('✅ Socket.IO Connected:', this.socket?.id);
      if (this.workspaceId) {
        this.joinWorkspace(this.workspaceId);
      }
    });

    this.socket.on('disconnect', () => {
      console.log('❌ Socket.IO Disconnected');
    });
  }

  disconnect() {
    if (this.socket) {
      if (this.workspaceId) {
        this.leaveWorkspace(this.workspaceId);
      }
      this.socket.disconnect();
      this.socket = null;
    }
  }

  joinWorkspace(workspaceId: string) {
    this.workspaceId = workspaceId;
    if (this.socket?.connected) {
      this.socket.emit('join_workspace', { workspace_id: workspaceId });
    }
  }

  leaveWorkspace(workspaceId: string) {
    if (this.socket?.connected) {
      this.socket.emit('leave_workspace', { workspace_id: workspaceId });
    }
    this.workspaceId = null;
  }

  get isConnected(): boolean {
    return this.socket?.connected || false;
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.socket) this.connect();
    this.socket?.on(event, callback);
  }

  off(event: string, callback: (data: any) => void) {
    this.socket?.off(event, callback);
  }

  // Subscribe to discovery events (kept for backwards compatibility)
  onDiscoveryEvent(event: string, callback: (data: any) => void) {
    this.on(event, callback);
    return () => {
      this.off(event, callback);
    };
  }
}

export const socketService = new SocketService();
