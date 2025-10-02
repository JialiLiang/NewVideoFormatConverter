import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiClient, resolveApiUrl } from '../api/client';
import type { ReactNode } from 'react';
import type { UserProfile } from '../types/user';

type AuthContextValue = {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  login: () => void;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      const response = await apiClient.get<UserProfile>('/api/me');
      setUser(response.data);
      setError(null);
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setUser(null);
        setError(null);
      } else {
        setError('Unable to verify session');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  const login = useCallback(() => {
    window.location.assign(resolveApiUrl('/api/auth/google/login'));
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/api/auth/logout');
    } finally {
      setUser(null);
      setError(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    await fetchUser();
  }, [fetchUser]);

  const value = useMemo(
    () => ({ user, isLoading, error, login, logout, refresh }),
    [user, isLoading, error, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
