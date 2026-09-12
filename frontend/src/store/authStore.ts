import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  company_id: string;
  company_name: string;
  avatar_path: string | null;
  is_active: boolean;
  email_verified: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthState {
  user: AuthUser | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string, remember_me?: boolean) => Promise<void>;
  register: (company_name: string, name: string, email: string, password: string, confirm_password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  forgotPassword: (email: string) => Promise<string>;
  clearError: () => void;
  setTokens: (tokens: AuthTokens) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password, remember_me = false) => {
        set({ isLoading: true, error: null });
        try {
          const res = await apiClient.post('/auth/login', { email, password, remember_me });
          const { user, tokens } = res.data;
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (err: any) {
          const message = err.response?.data?.detail || err.response?.data?.message || 'Login failed';
          set({ error: message, isLoading: false });
          throw new Error(message);
        }
      },

      register: async (company_name, name, email, password, confirm_password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await apiClient.post('/auth/register', {
            company_name,
            name,
            email,
            password,
            confirm_password,
          });
          const { user, tokens } = res.data;
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (err: any) {
          const message = err.response?.data?.detail || err.response?.data?.message || 'Registration failed';
          set({ error: message, isLoading: false });
          throw new Error(message);
        }
      },

      logout: async () => {
        try {
          await apiClient.post('/auth/logout');
        } catch {
          // Ignore logout errors — clear local state anyway
        }
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshToken: async () => {
        const { tokens } = get();
        if (!tokens?.refresh_token) {
          set({ user: null, tokens: null, isAuthenticated: false });
          return;
        }
        try {
          const res = await apiClient.post('/auth/refresh', {
            refresh_token: tokens.refresh_token,
          });
          set({ tokens: res.data });
        } catch {
          set({ user: null, tokens: null, isAuthenticated: false });
        }
      },

      fetchProfile: async () => {
        try {
          const res = await apiClient.get('/auth/me');
          set({ user: res.data, isAuthenticated: true });
        } catch {
          set({ user: null, tokens: null, isAuthenticated: false });
        }
      },

      forgotPassword: async (email) => {
        set({ isLoading: true, error: null });
        try {
          const res = await apiClient.post('/auth/forgot-password', { email });
          set({ isLoading: false });
          return res.data.message || 'If an account with that email exists, a reset link has been sent.';
        } catch (err: any) {
          const message = err.response?.data?.detail || 'Request failed';
          set({ error: message, isLoading: false });
          throw new Error(message);
        }
      },

      clearError: () => set({ error: null }),

      setTokens: (tokens) => set({ tokens }),
    }),
    {
      name: 'lead-intel-auth',
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
