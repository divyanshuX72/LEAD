import { apiClient } from '@/api/client';

export interface Setting {
  key: string;
  value: string | null;
  category: string;
}

export const SettingsService = {
  getAll: async (): Promise<Setting[]> => {
    const res = await apiClient.get('/settings');
    return res.data;
  },

  update: async (key: string, value: string): Promise<Setting> => {
    const res = await apiClient.post('/settings', { key, value });
    return res.data;
  },
};
