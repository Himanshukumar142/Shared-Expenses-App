import React, { useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout, isAuthenticated } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            {/* Logo */}
            <Link to="/" className="flex-shrink-0 flex items-center">
              <span className="text-xl font-bold text-primary-500 tracking-tight flex items-center gap-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                FairShare
              </span>
            </Link>
            
            {/* Navigation links */}
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              <Link
                to="/"
                className="border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition"
              >
                Dashboard
              </Link>
              <Link
                to="/import"
                className="border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition"
              >
                CSV Import
              </Link>
            </div>
          </div>
          
          {/* User actions */}
          <div className="flex items-center sm:ml-6">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-slate-700 bg-slate-100 py-1.5 px-3 rounded-full flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block animate-pulse"></span>
                User: {user?.username}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-red-500 hover:text-red-700 hover:bg-red-50 py-1.5 px-3 rounded-lg border border-red-200 transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
