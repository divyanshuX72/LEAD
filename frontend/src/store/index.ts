import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface GlobalState {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useStore = create<GlobalState>()(
  persist(
    (set) => ({
      isSidebarOpen: true,
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
    }),
    {
      name: 'lead-app-store',
    }
  )
);
