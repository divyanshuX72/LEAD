import { apiClient as api } from '../api/client';
import type { 
  LeadBatch, 
  Lead, 
  ExportJob, 
  DashboardStats 
} from '../types/lead';

export const LeadAgentService = {
  // Search
  startSearch: async (keywords: string[], location: string, limit: number = 50): Promise<{ batch_id: string }> => {
    const response = await api.post(`/leads/search`, { keywords, location, limit });
    return response.data;
  },

  stopSearch: async (batchId: string): Promise<void> => {
    await api.post(`/leads/${batchId}/stop`);
  },

  // Dashboard
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get(`/leads/dashboard/stats`);
    return response.data;
  },

  // Batches
  getBatches: async (limit: number = 100): Promise<LeadBatch[]> => {
    const response = await api.get(`/leads/lead-batches`, { params: { limit } });
    return response.data;
  },

  getBatch: async (batchId: string): Promise<LeadBatch> => {
    const response = await api.get(`/leads/lead-batches/${batchId}`);
    return response.data;
  },

  getBatchLeads: async (batchId: string, skip: number = 0, limit: number = 500): Promise<Lead[]> => {
    const response = await api.get(`/leads/lead-batches/${batchId}/leads`, { params: { skip, limit } });
    return response.data;
  },

  deleteBatch: async (batchId: string): Promise<void> => {
    await api.delete(`/leads/lead-batches/${batchId}`);
  },

  // Leads
  getLeads: async (query?: string, skip: number = 0, limit: number = 50): Promise<Lead[]> => {
    const response = await api.get(`/leads/leads`, { params: { query, skip, limit } });
    return response.data;
  },

  deleteLead: async (leadId: string): Promise<void> => {
    await api.delete(`/leads/leads/${leadId}`);
  },

  // Exports
  exportBatch: async (batchId: string, format: 'csv' | 'xlsx' = 'csv'): Promise<ExportJob> => {
    const response = await api.post(`/leads/exports/batch/${batchId}`, { format });
    return response.data;
  },

  exportSelectedBatches: async (batchIds: string[], format: 'csv' | 'xlsx' = 'csv'): Promise<ExportJob> => {
    const response = await api.post(`/leads/exports/selected`, { batch_ids: batchIds, format });
    return response.data;
  },

  exportAll: async (format: 'csv' | 'xlsx' = 'csv', uniqueOnly: boolean = false): Promise<ExportJob> => {
    const response = await api.post(`/leads/exports/all`, { format, unique_only: uniqueOnly });
    return response.data;
  },

  downloadExport: async (exportId: string): Promise<void> => {
    const response = await api.get(`/leads/exports/${exportId}/download`, {
      responseType: 'blob',
    });

    // Extract filename from header
    const contentDisposition = response.headers['content-disposition'];
    let filename = `export_${exportId}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    } else {
      const contentType = response.headers['content-type'] as string | undefined;
      if (contentType?.includes('spreadsheetml')) filename += '.xlsx';
      else if (contentType?.includes('csv')) filename += '.csv';
    }

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }
};
