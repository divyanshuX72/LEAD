import { create } from 'zustand';
import type { SearchProgress } from '@/types';

interface LeadState {
  activeSearch: SearchProgress | null;
  setActiveSearch: (search: SearchProgress | null) => void;
  updateSearchProgress: (updates: Partial<SearchProgress>) => void;
}

export const useLeadStore = create<LeadState>((set) => ({
  activeSearch: null,
  setActiveSearch: (search) => set({ activeSearch: search }),
  updateSearchProgress: (updates) => 
    set((state) => ({ 
      activeSearch: state.activeSearch ? { ...state.activeSearch, ...updates } : null 
    })),
}));
