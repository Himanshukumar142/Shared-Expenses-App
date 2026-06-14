import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const CSVImport = () => {
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Response stats
  const [report, setReport] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  
  const navigate = useNavigate();

  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const response = await api.get('/groups/');
        setGroups(response.data);
        if (response.data.length > 0) {
          setSelectedGroupId(response.data[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch groups:", err);
      }
    };
    fetchGroups();
  }, []);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError('');
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please choose a CSV file to upload.");
      return;
    }
    if (!selectedGroupId) {
      setError("Please select a target group for imports.");
      return;
    }

    setLoading(true);
    setError('');
    setReport(null);
    setAnomalies([]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('group_id', selectedGroupId);

    try {
      const response = await api.post('/import/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setReport(response.data.report_summary);
      setAnomalies(response.data.anomalies);
    } catch (err) {
      console.error("CSV Import failed:", err);
      setError(err.response?.data?.error || "Error importing CSV file. Make sure file format is valid.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-8">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload Spreadsheet Data</h1>
          <p className="text-sm text-slate-500 mt-1">
            Select a target billing group and upload your `expenses_export.csv` file exactly as provided.
          </p>

          <form onSubmit={handleUpload} className="space-y-6 mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Target Group
                </label>
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="w-full px-3 py-2.5 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {groups.map((group) => (
                    <option key={group.id} value={group.id}>{group.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Choose CSV File
                </label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="w-full px-3 py-2 border border-slate-350 rounded-lg text-sm file:mr-4 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-2.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Parsing & Auditing CSV...
                </>
              ) : (
                'Import Spreadsheet'
              )}
            </button>
          </form>
        </div>

        {/* Import Report Result Card */}
        {report && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Import Report Summary</h2>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-center">
                  <div className="text-2xl font-black text-slate-900">{report.total_rows}</div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mt-1">Total Rows</div>
                </div>
                <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100 text-center">
                  <div className="text-2xl font-black text-emerald-700">{report.imported_rows}</div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-500 mt-1">Imported</div>
                </div>
                <div className="bg-amber-50 p-4 rounded-xl border border-amber-100 text-center">
                  <div className="text-2xl font-black text-amber-700">{report.flagged_rows}</div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-amber-500 mt-1">Review Needed</div>
                </div>
                <div className="bg-red-50 p-4 rounded-xl border border-red-100 text-center">
                  <div className="text-2xl font-black text-red-700">{report.rejected_rows}</div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-red-500 mt-1">Rejected</div>
                </div>
              </div>

              {report.flagged_rows > 0 && (
                <div className="mt-6 p-4 bg-amber-50 text-amber-800 rounded-xl border border-amber-200 text-sm flex justify-between items-center">
                  <span>
                    Meera's check triggered! <strong>{report.flagged_rows}</strong> records are pending review (duplicates/warnings).
                  </span>
                  <button
                    onClick={() => navigate(`/import-report/${report.job_id}`)}
                    className="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-1.5 px-3 rounded-lg text-xs transition whitespace-nowrap"
                  >
                    Open Review Screen
                  </button>
                </div>
              )}
            </div>

            {/* Row Level Details List */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Detailed Scanned Anomalies ({anomalies.length})</h2>
              
              {anomalies.length === 0 ? (
                <div className="text-center text-slate-400 py-6 text-sm">
                  No anomalies detected in the CSV. All records imported clean!
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm text-left">
                    <thead>
                      <tr className="text-slate-400 font-bold uppercase tracking-wider text-xs">
                        <th className="pb-3 pr-4">Row</th>
                        <th className="pb-3 px-4">Anomaly Type</th>
                        <th className="pb-3 px-4">Severity</th>
                        <th className="pb-3 pl-4">Action Taken</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {anomalies.map((a) => (
                        <tr key={a.id} className="hover:bg-slate-50/50 transition">
                          <td className="py-3.5 pr-4 font-bold text-slate-900">#{a.row_number}</td>
                          <td className="py-3.5 px-4 font-semibold text-slate-800">{a.anomaly_type}</td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${a.severity === 'error' ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-amber-50 text-amber-600 border border-amber-200'}`}>
                              {a.severity}
                            </span>
                          </td>
                          <td className="py-3.5 pl-4 text-xs text-slate-500 max-w-xs truncate">{a.action_taken}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CSVImport;
