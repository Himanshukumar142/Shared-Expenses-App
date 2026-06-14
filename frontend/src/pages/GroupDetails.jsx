import React, { useState, useEffect, useContext } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';
import { AuthContext } from '../context/AuthContext';

const GroupDetails = () => {
  const { id } = useParams();
  const { user } = useContext(AuthContext);

  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [balancesData, setBalancesData] = useState(null);
  const [selectedUserLedger, setSelectedUserLedger] = useState(null);
  const [selectedUsername, setSelectedUsername] = useState('');

  // Modals state
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showSettlementModal, setShowSettlementModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(false);

  // Add Expense form state
  const [expTitle, setExpTitle] = useState('');
  const [expDesc, setExpDesc] = useState('');
  const [expAmount, setExpAmount] = useState('');
  const [expCurrency, setExpCurrency] = useState('INR');
  const [expRate, setExpRate] = useState('1');
  const [expPayer, setExpPayer] = useState('');
  const [expDate, setExpDate] = useState(new Date().toISOString().split('T')[0]);
  const [expSplitType, setExpSplitType] = useState('equal');
  const [manualSplits, setManualSplits] = useState({}); // { username: amount/percentage/share }
  const [expLoading, setExpLoading] = useState(false);

  // Add Settlement form state
  const [setSettlePayer, setSetSettlePayer] = useState('');
  const [setSettlePayee, setSetSettlePayee] = useState('');
  const [setSettleAmount, setSetSettleAmount] = useState('');
  const [setSettleDate, setSetSettleDate] = useState(new Date().toISOString().split('T')[0]);
  const [setLoadingState, setSetLoadingState] = useState(false);

  // Add Member form state
  const [newMemberUserId, setNewMemberUserId] = useState('');
  const [newMemberJoined, setNewMemberJoined] = useState(new Date().toISOString().split('T')[0]);
  const [newMemberLeft, setNewMemberLeft] = useState('');
  const [memberLoading, setMemberLoading] = useState(false);
  const [allSystemUsers, setAllSystemUsers] = useState([]);

  // Fetch initial group info and calculations
  const loadData = async () => {
    try {
      const groupRes = await api.get(`/groups/${id}/`);
      setGroup(groupRes.data);
      
      const balancesRes = await api.get(`/groups/${id}/balances/`);
      setBalancesData(balancesRes.data);
      
      // Load system users for Add Member dropdown
      const usersRes = await api.get('/users/');
      setAllSystemUsers(usersRes.data);
      
      // Default set first payer
      if (groupRes.data.members?.length > 0) {
        setExpPayer(groupRes.data.members[0].user_id);
        setSetSettlePayer(groupRes.data.members[0].user_id);
        setSetSettlePayee(groupRes.data.members[1]?.user_id || '');
      }
    } catch (err) {
      console.error("Error loading group details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  // Handle currency swap to prefill standard exchange rates (Priya's request)
  useEffect(() => {
    if (expCurrency === 'USD') {
      setExpRate('83');
    } else {
      setExpRate('1');
    }
  }, [expCurrency]);

  const handleAddExpense = async (e) => {
    e.preventDefault();
    setExpLoading(true);
    
    // Build nested split payload if split_type is not 'equal'
    const splitsPayload = [];
    if (expSplitType !== 'equal') {
      // Calculate or parse input splits
      group.members.forEach((m) => {
        const val = manualSplits[m.username] || 0;
        let itemAmount = 0;
        let percentage = null;
        let share = null;
        
        if (expSplitType === 'exact') {
          itemAmount = parseFloat(val);
        } else if (expSplitType === 'percentage') {
          percentage = parseFloat(val);
          itemAmount = (percentage / 100) * parseFloat(expAmount);
        } else if (expSplitType === 'share') {
          share = parseInt(val);
          // Amount is calculated by backend based on shares
          itemAmount = 0; 
        }

        splitsPayload.push({
          user_id: m.user_id,
          amount: itemAmount,
          percentage: percentage,
          share: share
        });
      });
    }

    try {
      await api.post('/expenses/', {
        group: id,
        title: expTitle,
        description: expDesc,
        amount: parseFloat(expAmount),
        currency: expCurrency,
        exchange_rate: parseFloat(expRate),
        paid_by_id: parseInt(expPayer),
        expense_date: expDate,
        split_type: expSplitType,
        splits: splitsPayload
      });
      
      // Reset & Reload
      setExpTitle('');
      setExpDesc('');
      setExpAmount('');
      setManualSplits({});
      setShowExpenseModal(false);
      loadData();
    } catch (err) {
      console.error("Failed to add expense:", err);
      alert(err.response?.data?.non_field_errors?.[0] || err.response?.data?.splits?.[0] || "Failed to create expense. Check your splitting rules.");
    } finally {
      setExpLoading(false);
    }
  };

  const handleAddSettlement = async (e) => {
    e.preventDefault();
    if (setSettlePayer === setSettlePayee) {
      alert("Payer and payee cannot be the same person.");
      return;
    }
    
    setSetLoadingState(true);
    try {
      await api.post('/settlements/', {
        group: id,
        payer_id: parseInt(setSettlePayer),
        payee_id: parseInt(setSettlePayee),
        amount: parseFloat(setSettleAmount),
        currency: 'INR',
        settled_at: setSettleDate
      });
      
      setSetSettleAmount('');
      setShowSettlementModal(false);
      loadData();
    } catch (err) {
      console.error("Failed to record settlement:", err);
      alert("Error recording settlement.");
    } finally {
      setSetLoadingState(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMemberUserId) {
      alert("Please select a user.");
      return;
    }
    setMemberLoading(true);
    
    try {
      await api.post(`/groups/${id}/members/`, {
        user_id: parseInt(newMemberUserId),
        joined_at: newMemberJoined,
        left_at: newMemberLeft || null
      });

      setNewMemberUserId('');
      setNewMemberLeft('');
      setShowMemberModal(false);
      loadData();
    } catch (err) {
      console.error("Failed to add member:", err);
      alert(err.response?.data?.error || "Error adding member. Make sure they are not already a member.");
    } finally {
      setMemberLoading(false);
    }
  };

  const handleViewTraceability = (username) => {
    const userData = balancesData?.balances?.[username];
    if (userData) {
      setSelectedUserLedger(userData.ledger);
      setSelectedUsername(username);
    }
  };

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(amt);
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
      {/* Breadcrumb */}
      <Link to="/" className="text-sm font-semibold text-primary-500 hover:text-primary-600 mb-4 inline-block">
        &larr; Back to Groups Dashboard
      </Link>

      <div className="flex flex-col lg:flex-row justify-between items-start gap-8">
        
        {/* Left Side Content: Group Members, Balances, Settlements */}
        <div className="w-full lg:w-2/3 space-y-8">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{group?.name}</h1>
            <p className="text-slate-500 mt-1 text-sm">{group?.description}</p>
            
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={() => setShowExpenseModal(true)}
                className="bg-primary-500 hover:bg-primary-600 text-white font-semibold py-2 px-4 rounded-xl shadow-sm text-sm transition"
              >
                Add Expense
              </button>
              <button
                onClick={() => setShowSettlementModal(true)}
                className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold py-2 px-4 rounded-xl shadow-sm text-sm transition"
              >
                Record Payment
              </button>
              <button
                onClick={() => setShowMemberModal(true)}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2 px-4 rounded-xl text-sm transition"
              >
                Add Member Timeline
              </button>
            </div>
          </div>

          {/* Members active intervals */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Membership Timeline</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {group?.members?.map((m) => (
                <div key={m.id} className="border border-slate-150 p-4 rounded-xl flex flex-col justify-between">
                  <span className="font-bold text-slate-800">{m.username}</span>
                  <div className="text-xs text-slate-500 mt-2 space-y-0.5">
                    <div>Joined: <span className="font-medium">{m.joined_at}</span></div>
                    <div>Left: <span className="font-medium">{m.left_at || 'Active (Indefinitely)'}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Aisha's Settlements Simplification Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-1">Aisha's Settle Summary</h2>
            <p className="text-xs text-slate-500 mb-4">Simplified list of transactions to clear all debts. No redundant transfers.</p>
            
            {balancesData?.simplified_settlements?.length === 0 ? (
              <div className="bg-emerald-50 text-emerald-800 p-4 rounded-xl font-semibold text-center text-sm border border-emerald-100">
                &bull; Everyone is fully settled! No debts to pay.
              </div>
            ) : (
              <div className="space-y-3">
                {balancesData?.simplified_settlements?.map((s, idx) => (
                  <div key={idx} className="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-slate-200">
                    <div className="text-sm font-semibold text-slate-700">
                      <span className="text-red-500">{s.from_user}</span> pays <span className="text-emerald-600">{s.to_user}</span>
                    </div>
                    <div className="text-base font-extrabold text-slate-900">
                      {formatCurrency(s.amount)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Side Content: Balance Summary Card */}
        <div className="w-full lg:w-1/3 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sticky top-24">
            <h2 className="text-xl font-bold text-slate-900 mb-2">Individual Balances</h2>
            <p className="text-xs text-slate-500 mb-4">Click "Why?" to drilldown the exact list of expenses making up the balance (Rohan's request).</p>
            
            <div className="space-y-4">
              {balancesData?.balances && Object.entries(balancesData.balances).map(([username, info]) => {
                const isOwed = info.net_balance < 0;
                return (
                  <div key={username} className="flex justify-between items-center border-b border-slate-100 pb-3 last:border-none last:pb-0">
                    <div>
                      <div className="font-bold text-slate-800">{username}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Paid: {formatCurrency(info.total_paid_expenses)} | Owed: {formatCurrency(info.total_owed_splits)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-extrabold text-sm ${info.net_balance > 0.01 ? 'text-green-600' : info.net_balance < -0.01 ? 'text-red-500' : 'text-slate-400'}`}>
                        {info.net_balance > 0.01 ? '+' : ''}
                        {formatCurrency(info.net_balance)}
                      </div>
                      <button
                        onClick={() => handleViewTraceability(username)}
                        className="text-[10px] text-primary-500 font-semibold hover:underline block ml-auto mt-0.5"
                      >
                        Why?
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Rohan's Traceability Sidebar/Panel Overlay */}
      {selectedUserLedger && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex justify-end z-50 animate-in fade-in duration-150">
          <div className="bg-white w-full max-w-md h-full shadow-2xl p-6 overflow-y-auto flex flex-col justify-between animate-in slide-in-from-right duration-250">
            <div>
              <div className="flex justify-between items-center border-b border-slate-200 pb-4 mb-6">
                <div>
                  <h3 className="text-xl font-bold text-slate-900">Ledger Statement</h3>
                  <p className="text-xs text-slate-500">Itemized audit list for user: {selectedUsername}</p>
                </div>
                <button
                  onClick={() => setSelectedUserLedger(null)}
                  className="text-slate-400 hover:text-slate-600 transition"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                {selectedUserLedger.map((item, idx) => {
                  const isPositive = item.amount > 0;
                  return (
                    <div key={idx} className="flex justify-between items-start bg-slate-50 p-3.5 rounded-xl border border-slate-150">
                      <div>
                        <div className="font-bold text-sm text-slate-800">{item.title}</div>
                        <div className="text-[10px] text-slate-400 mt-1">{item.date}</div>
                      </div>
                      <span className={`font-extrabold text-sm ${isPositive ? 'text-green-600' : 'text-red-500'}`}>
                        {isPositive ? '+' : ''}
                        {formatCurrency(item.amount)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-slate-200 pt-6 mt-6 flex justify-between items-center font-bold text-slate-800">
              <span>Total Current Balance</span>
              <span className={balancesData?.balances?.[selectedUsername]?.net_balance > 0.01 ? 'text-green-600' : balancesData?.balances?.[selectedUsername]?.net_balance < -0.01 ? 'text-red-500' : 'text-slate-400'}>
                {formatCurrency(balancesData?.balances?.[selectedUsername]?.net_balance || 0)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Add Expense Modal */}
      {showExpenseModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex justify-center items-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-slate-900">Add Group Expense</h3>
              <button onClick={() => setShowExpenseModal(false)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleAddExpense} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={expTitle}
                    onChange={(e) => setExpTitle(e.target.value)}
                    placeholder="e.g. WiFi Bill"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Expense Date</label>
                  <input
                    type="date"
                    required
                    value={expDate}
                    onChange={(e) => setExpDate(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={expAmount}
                    onChange={(e) => setExpAmount(e.target.value)}
                    placeholder="1200"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Currency</label>
                  <select
                    value={expCurrency}
                    onChange={(e) => setExpCurrency(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Exchange Rate</label>
                  <input
                    type="number"
                    step="0.000001"
                    required
                    value={expRate}
                    onChange={(e) => setExpRate(e.target.value)}
                    placeholder="1"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Paid By</label>
                  <select
                    value={expPayer}
                    onChange={(e) => setExpPayer(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {group?.members?.map((m) => (
                      <option key={m.user_id} value={m.user_id}>{m.username}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Split Type</label>
                  <select
                    value={expSplitType}
                    onChange={(e) => setExpSplitType(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    <option value="equal">Split Equally</option>
                    <option value="exact">Exact Amounts (Unequal)</option>
                    <option value="percentage">Percentages</option>
                    <option value="share">Share Ratios</option>
                  </select>
                </div>
              </div>

              {expSplitType !== 'equal' && (
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <h4 className="text-xs font-bold text-slate-700 uppercase mb-3">Individual Split Shares</h4>
                  <div className="space-y-3">
                    {group?.members?.map((m) => (
                      <div key={m.id} className="flex justify-between items-center">
                        <span className="text-sm font-semibold text-slate-700">{m.username}</span>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="0.01"
                            value={manualSplits[m.username] || ''}
                            onChange={(e) => setManualSplits({...manualSplits, [m.username]: e.target.value})}
                            placeholder={expSplitType === 'exact' ? '₹ amount' : expSplitType === 'percentage' ? '% ratio' : 'share'}
                            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm text-right w-28"
                          />
                          <span className="text-xs text-slate-400 font-semibold">
                            {expSplitType === 'exact' ? 'INR' : expSplitType === 'percentage' ? '%' : 'shares'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Notes</label>
                <textarea
                  value={expDesc}
                  onChange={(e) => setExpDesc(e.target.value)}
                  placeholder="Optional details (e.g., flight numbers or rent items)"
                  rows={2}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowExpenseModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={expLoading}
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-semibold transition"
                >
                  {expLoading ? 'Adding...' : 'Add Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Settlement Modal */}
      {showSettlementModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex justify-center items-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-slate-900">Record Direct Payment</h3>
              <button onClick={() => setShowSettlementModal(false)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleAddSettlement} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Payer (Who Paid)</label>
                  <select
                    value={setSettlePayer}
                    onChange={(e) => setSetSettlePayer(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {group?.members?.map((m) => (
                      <option key={m.user_id} value={m.user_id}>{m.username}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Payee (Who Received)</label>
                  <select
                    value={setSettlePayee}
                    onChange={(e) => setSetSettlePayee(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {group?.members?.map((m) => (
                      <option key={m.user_id} value={m.user_id}>{m.username}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Amount (INR)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={setSettleAmount}
                    onChange={(e) => setSetSettleAmount(e.target.value)}
                    placeholder="700"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Date Paid</label>
                  <input
                    type="date"
                    required
                    value={setSettleDate}
                    onChange={(e) => setSetSettleDate(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSettlementModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={setLoadingState}
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-semibold transition"
                >
                  {setLoadingState ? 'Recording...' : 'Record Payment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showMemberModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex justify-center items-center p-4 z-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-slate-900">Add Member Timeline</h3>
              <button onClick={() => setShowMemberModal(false)} className="text-slate-400 hover:text-slate-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Select User</label>
                <select
                  required
                  value={newMemberUserId}
                  onChange={(e) => setNewMemberUserId(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="">-- Select flatmate user --</option>
                  {allSystemUsers.map((user_obj) => (
                    <option key={user_obj.id} value={user_obj.id}>
                      {user_obj.username}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Joined Date</label>
                  <input
                    type="date"
                    required
                    value={newMemberJoined}
                    onChange={(e) => setNewMemberJoined(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">Left Date</label>
                  <input
                    type="date"
                    value={newMemberLeft}
                    onChange={(e) => setNewMemberLeft(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowMemberModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={memberLoading}
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-semibold transition"
                >
                  {memberLoading ? 'Adding...' : 'Add Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default GroupDetails;
