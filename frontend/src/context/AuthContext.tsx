import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { DoctorUser, LoginCredentials } from '../types/triage';
import { ApiService, TOKEN_STORAGE_KEY } from '../services/api';

interface AuthContextType {
  currentUser: DoctorUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  sessionExpired: boolean;
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error: string | null }>;
  logout: () => void;
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<DoctorUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [sessionExpired, setSessionExpired] = useState<boolean>(false);

  // Client-side resilient logout: clears storage and local state immediately
  const logout = useCallback(() => {
    ApiService.setToken(null);
    setCurrentUser(null);
    setToken(null);
    setSessionExpired(false);
    // Attempt backend logout notice, but never let failure abort client logout
    ApiService.logout().catch(() => {});
  }, []);

  const clearSessionExpired = useCallback(() => {
    setSessionExpired(false);
  }, []);

  // Recursion-safe startup auth initialization
  useEffect(() => {
    let isMounted = true;

    // Register 401 callback for protected clinician requests
    ApiService.setOnUnauthorized(() => {
      if (!isMounted) return;
      ApiService.setToken(null);
      setCurrentUser(null);
      setToken(null);
      setSessionExpired(true);
    });

    const initAuth = async () => {
      let savedToken: string | null = null;
      try {
        savedToken = sessionStorage.getItem(TOKEN_STORAGE_KEY);
      } catch {}

      if (!savedToken) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      // Initial validation: call GET /auth/me with suppressUnauthorized=true to prevent loops
      const { doctor, error } = await ApiService.getMe(savedToken);

      if (!isMounted) return;

      if (doctor && !error) {
        setCurrentUser(doctor);
        setToken(savedToken);
        ApiService.setToken(savedToken);
      } else {
        // Invalid or expired token: clear without triggering recursive error handlers
        ApiService.setToken(null);
        setCurrentUser(null);
        setToken(null);
      }

      setIsLoading(false);
    };

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (
    credentials: LoginCredentials
  ): Promise<{ success: boolean; error: string | null }> => {
    setSessionExpired(false);
    const { data, error } = await ApiService.login(credentials);

    if (data?.access_token && data?.doctor) {
      setToken(data.access_token);
      setCurrentUser(data.doctor);
      ApiService.setToken(data.access_token);
      return { success: true, error: null };
    }

    return {
      success: false,
      error: error || 'Invalid username or password. Please verify your credentials.',
    };
  };

  const value: AuthContextType = {
    currentUser,
    token,
    isAuthenticated: Boolean(currentUser && token),
    isLoading,
    sessionExpired,
    login,
    logout,
    clearSessionExpired,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
