import React, { createContext, useContext, useState, useEffect } from 'react';
import apiService from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      const token = localStorage.getItem('accessToken');
      const storedUser = localStorage.getItem('adminUser');

      if (!token || !storedUser) {
        setLoading(false);
        return;
      }

      try {
        const me = await apiService.getCurrentUser();
        const currentUser = me.data.user;
        setUser(currentUser);
        localStorage.setItem('adminUser', JSON.stringify(currentUser));
      } catch (error) {
        apiService.clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await apiService.login(email, password);
      const { access_token, refresh_token, user: userData } = response.data;

      apiService.setTokens(access_token, refresh_token);
      setUser(userData);
      localStorage.setItem('adminUser', JSON.stringify(userData));

      return { success: true };
    } catch (error) {
      const message = error?.response?.data?.error || 'Login failed';
      return { success: false, error: message };
    }
  };

  const logout = () => {
    setUser(null);
    apiService.clearTokens();
    localStorage.removeItem('adminEmail');
  };

  const isAuthenticated = () => {
    return !!user;
  };

  const value = {
    user,
    login,
    logout,
    isAuthenticated,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
