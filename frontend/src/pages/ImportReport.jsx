import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../api';

const ImportReport = () => {
  const { id } = useParams();
  
  const [job, setJob] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [targetGroupId, setTargetGroupId] = useState('');
  const [groups, setGroups] = useState([]);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const navigate = useNavigate();

  const loadReport = async () => {
    try {
      const response = await api.get(`/import-report/${id}/`);
      setJob(response.data);
      setAnomalies(response.data.anomalies);
      
      // Load groups to resolve target
      const groupsRes = await api.get('/groups/');
      setGroups(groupsRes.data);
      if (groupsRes.data.length > 0) {
        setTargetGroupId(groupsRes.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load report details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, [id]);

  const handleResolve = async (anomalyId, actionType) => {
    if (!targetGroupId) {
      alert("Please select a target group first.");
      return;
    }

    setActionLoadingId(anomalyId);
    try {
      await api.post(`/import-report/anomalies/${anomalyId}/approve/`, {
        action: actionType,
        group_id: parseInt(targetGroupId)
      });
      
      // Update local state to show updated status
      setAnomalies(anomalies.map(a => 
        a.id === anomalyId 
          ? { ...a, status: actionType === 'approve' ? 'approved' : 'rejected', action_taken: actionType === 'approve' ? 'Approved manually' : 'Rejected manually' } 
          : a
      ));
    } catch (err) {
      console.error("Failed to resolve anomaly:", err);
      alert(err.response?.data?.error || "Error updating anomaly status.");
    } finally {
      setActionLoadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link to="/import" className="text-xs font-semibold text-primary-500 hover:text-primary-600 mb-2 inline-block">
            &larr; Back to CSV Import Upload
          </Link>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Meera's Review Workflow</h1>
          <p className="text-sm text-slate-500 mt-1">
            File: <span className="font-semibold text-slate-700">{job?.file_name}</span> | Uploaded by: <span className="font-semibold text-slate-700">{job?.uploaded_by}</span>
          </p>
        </div>
        
        {/* Target selector */}
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex items-center gap-3">
          <label className="text-xs font-bold text-slate-600 uppercase">Target Group:</label>
          <select
            value={targetGroupId}
            onChange={(e) => setTargetGroupId(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-white font-medium"
          >
            {groups.map(g => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-6">
        {anomalies.map((a) => {
          const isPending = a.status === 'pending_review';
          return (
            <div
              key={a.id}
              className={`bg-white border rounded-2xl shadow-sm p-6 transition flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${isPending ? 'border-amber-250 bg-amber-50/5' : a.status === 'approved' ? 'border-green-200' : 'border-slate-200 opacity-60'}`}
            >
              <div className="space-y-2 max-w-xl">
                <div className="flex items-center gap-2">
                  <span className="bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded-lg text-xs">
                    Row #{a.row_number}
                  </span>
                  <span className="font-bold text-slate-900 text-sm">
                    {a.anomaly_type}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${a.status === 'pending_review' ? 'bg-amber-100 text-amber-700' : a.status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                    {a.status.replace('_', ' ')}
                  </span>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed">
                  <strong>Validation Result:</strong> {a.action_taken}
                </p>

                {/* Inspect raw data container */}
                <div className="bg-slate-50 border border-slate-200/60 p-3 rounded-xl text-[11px] text-slate-600 font-mono grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
                  <div><strong>Date:</strong> {a.row_data.date || 'N/A'}</div>
                  <div><strong>Desc:</strong> {a.row_data.description || 'N/A'}</div>
                  <div><strong>Payer:</strong> {a.row_data.paid_by || 'N/A'}</div>
                  <div><strong>Amount:</strong> {a.row_data.amount || 'N/A'} {a.row_data.currency}</div>
                  <div className="col-span-2"><strong>Split With:</strong> {a.row_data.split_with || 'N/A'}</div>
                  <div className="col-span-2"><strong>Details:</strong> {a.row_data.split_details || 'N/A'}</div>
                </div>
              </div>

              {/* Review buttons */}
              {isPending ? (
                <div className="flex gap-2.5 w-full md:w-auto">
                  <button
                    onClick={() => handleResolve(a.id, 'reject')}
                    disabled={actionLoadingId === a.id}
                    className="flex-1 md:flex-none border border-red-200 hover:bg-red-50 text-red-600 font-semibold py-2 px-4 rounded-xl text-xs transition"
                  >
                    Reject Row
                  </button>
                  <button
                    onClick={() => handleResolve(a.id, 'approve')}
                    disabled={actionLoadingId === a.id}
                    className="flex-1 md:flex-none bg-primary-500 hover:bg-primary-600 text-white font-semibold py-2 px-4 rounded-xl text-xs shadow-sm transition"
                  >
                    {actionLoadingId === a.id ? 'Processing...' : 'Approve & Import'}
                  </button>
                </div>
              ) : (
                <span className="text-xs text-slate-400 font-semibold italic">
                  Reviewed: Action Locked
                </span>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Return footer */}
      <div className="mt-8 text-center">
        <Link
          to={`/groups/${targetGroupId}`}
          className="inline-flex items-center justify-center bg-primary-500 hover:bg-primary-600 text-white font-semibold py-2.5 px-6 rounded-xl transition"
        >
          Check Updated Balances Dashboard &rarr;
        </Link>
      </div>
    </div>
  );
};

export default ImportReport;
