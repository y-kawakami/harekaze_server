/**
 * 認証状態管理フック
 * Requirements: 6.5
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import type { Annotator } from '../types/api';
import { login as apiLogin, getMe } from '../api/client';

interface AuthContextType {
  annotator: Annotator | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [annotator, setAnnotator] = useState<Annotator | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('annotation_token');
    if (!token) {
      setAnnotator(null);
      setIsLoading(false);
      return;
    }

    try {
      const user = await getMe();
      setAnnotator(user);
    } catch {
      localStorage.removeItem('annotation_token');
      setAnnotator(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    localStorage.setItem('annotation_token', result.access_token);
    const user = await getMe();
    setAnnotator(user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('annotation_token');
    setAnnotator(null);
  }, []);

  const value: AuthContextType = {
    annotator,
    isLoading,
    isAuthenticated: !!annotator,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
