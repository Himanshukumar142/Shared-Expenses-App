import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { AuthContext } from '../context/AuthContext';

const Dashboard = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Group creation form state
  const [showModal, setShowModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  const { user } = useContext(AuthContext);

  const fetchGroups = async () => {
    try {
      const response = await api.get('/groups/');
      setGroups(response.data);
    } catch (err) {
      console.error("Failed to load groups:", err);
      setError("Unable to load groups. Please check your backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.strip) {
      // String safety check
      if (newGroupName.trim() === '') return;
    }
    
    setCreateLoading(true);
    try {
      const response = await api.post('/groups/', {
        name: newGroupName,
        description: newGroupDesc
      });
      
      // Auto-join the creator to the group
      await api.post(`/groups/${response.data.id}/members/`, {
        user_id: 1, // Default user Aisha/creator id
        joined_at: new Date().toISOString().split('T')[0]
      });

      setNewGroupName('');
      setNewGroupDesc('');
      setShowModal(false);
      fetchGroups();
    } catch (err) {
      console.error("Failed to create group:", err);
      alert("Error creating group. Name might already exist.");
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header card */}
      <div className="bg-gradient-to-r from-primary-500 to-indigo-600 rounded-2xl p-6 md:p-8 text-white shadow-sm mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight">
          Welcome back, {user?.username}!
        </h1>
        <p className="mt-2 text-indigo-100 max-w-xl">
          Track shared bills, split expenses, and settle debts with Aisha's settlements simplification and Rohan's detailed expense traceability.
        </p>
      </div>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Your Expense Groups</h2>
          <p className="text-sm text-slate-500">Select a group below to view balances, details, or record settlements.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold py-2 px-4 rounded-xl shadow-sm transition"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Create Group
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-4 rounded-xl text-center">
          <span className="font-semibold">{error}</span>
          <button onClick={fetchGroups} className="block mx-auto mt-2 text-sm underline font-medium text-red-800">
            Retry Connection
          </button>
        </div>
      ) : groups.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm">
          <div className="text-slate-400 mb-4 flex justify-center">
            <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-slate-900">No Groups Found</h3>
          <p className="text-slate-500 mt-1 max-w-sm mx-auto text-sm">
            Create a group or click "Setup Default Flatmates Environment" on the login screen to import seed data immediately.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-6 inline-flex items-center gap-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold py-2 px-6 rounded-xl transition"
          >
            Create Your First Group
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map((group) => (
            <Link
              key={group.id}
              to={`/groups/${group.id}`}
              className="group bg-white border border-slate-200 hover:border-primary-300 hover:shadow-md p-6 rounded-2xl transition duration-200 flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold text-slate-900 group-hover:text-primary-500 transition">
                    {group.name}
                  </h3>
                  <span className="text-xs bg-slate-100 text-slate-600 py-1 px-2.5 rounded-full font-semibold">
                    {group.members?.length || 0} members
                  </span>
                </div>
                <p className="text-slate-500 text-sm line-clamp-2 mb-6">
                  {group.description || 'No description provided.'}
                </p>
              </div>
              <div className="border-t border-slate-100 pt-4 flex justify-between items-center text-xs font-semibold text-slate-400">
                <span>Created {new Date(group.created_at).toLocaleDateString()}</span>
                <span className="text-primary-500 group-hover:translate-x-1 transition flex items-center gap-0.5">
                  View Details &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Group Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex justify-center items-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-slate-900">Create New Group</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleCreateGroup} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Group Name
                </label>
                <input
                  type="text"
                  required
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="e.g. Flatmates 302"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Description
                </label>
                <textarea
                  value={newGroupDesc}
                  onChange={(e) => setNewGroupDesc(e.target.value)}
                  placeholder="Describe the group (optional)"
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-semibold transition disabled:opacity-50"
                >
                  {createLoading ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
