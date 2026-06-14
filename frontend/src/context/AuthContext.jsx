import React, { createContext, useState, useEffect } from 'react';
import api from '../api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if user session exists on mount
  useEffect(() => {
    const savedUsername = localStorage.getItem('username');
    const token = localStorage.getItem('access_token');
    
    if (savedUsername && token) {
      setUser({ username: savedUsername });
    }
    setLoading(false);
  }, []);

  // Login handler using simple jwt endpoint
  const login = async (username, password) => {
    try {
      const response = await api.post('/auth/login/', { username, password });
      const { access, refresh } = response.data;
      
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('username', username);
      
      setUser({ username });
      return { success: true };
    } catch (error) {
      console.error("Login failed:", error);
      const errorMsg = error.response?.data?.detail || "Invalid credentials. Please try again.";
      return { success: false, error: errorMsg };
    }
  };

  // Register handler
  const register = async (username, email, password) => {
    try {
      await api.post('/auth/register/', { username, email, password });
      // Automate login immediately after successful registration
      return await login(username, password);
    } catch (error) {
      console.error("Registration failed:", error);
      const errors = error.response?.data;
      let errorMsg = "Failed to register.";
      if (errors) {
        errorMsg = Object.values(errors).flat().join(" ") || errorMsg;
      }
      return { success: false, error: errorMsg };
    }
  };

  // Logout handler
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    setUser(null);
  };

  // Utility helper to boot default users (Aisha, Rohan, Priya, Meera, Sam, Dev) 
  // and set up default groups in the SQLite/PostgreSQL database instantly.
  const setupDefaultEnvironment = async () => {
    try {
      const response = await api.post('/setup/');
      // Automatically log in as Aisha (default password is Password123)
      await login('Aisha', 'Password123');
      return { success: true, data: response.data };
    } catch (error) {
      console.error("Setup failed:", error);
      return { success: false, error: error.response?.data?.error || "Setup failed." };
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, setupDefaultEnvironment, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};
