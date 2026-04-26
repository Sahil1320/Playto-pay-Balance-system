import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  getMerchantProfile,
  getMerchantBalance,
  getMerchantLedger,
  getMerchantPayouts,
  logout,
} from '../api/client';
import { Zap, LogOut, RefreshCw } from 'lucide-react';
import BalanceCards from '../components/BalanceCards';
import PayoutForm from '../components/PayoutForm';
import PayoutHistory from '../components/PayoutHistory';
import LedgerTable from '../components/LedgerTable';

export default function Dashboard({ onLogout }) {
  const navigate = useNavigate();
  const [merchant, setMerchant] = useState(null);
  const [balance, setBalance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const [profileRes, balanceRes, ledgerRes, payoutsRes] = await Promise.all([
        getMerchantProfile(),
        getMerchantBalance(),
        getMerchantLedger(),
        getMerchantPayouts(),
      ]);
      setMerchant(profileRes.data);
      setBalance(balanceRes.data);
      setLedger(ledgerRes.data.results || ledgerRes.data);
      setPayouts(payoutsRes.data.results || payoutsRes.data);
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
      } else {
        toast.error('Failed to load dashboard data');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 seconds for live status updates
    const interval = setInterval(() => fetchData(), 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleLogout = () => {
    logout();
    onLogout();
    navigate('/login');
    toast.success('Logged out');
  };

  const handlePayoutSuccess = () => {
    fetchData(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-accent-500/30 border-t-accent-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-surface-400 text-sm">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-surface-950/80 backdrop-blur-xl border-b border-surface-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-accent-500/20">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Playto Pay</h1>
                <p className="text-xs text-surface-500 -mt-0.5">{merchant?.business_name}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => fetchData(true)}
                className={`p-2 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800
                           transition-all duration-200 ${refreshing ? 'animate-spin' : ''}`}
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
              <button
                id="logout-btn"
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-surface-400 hover:text-white
                           hover:bg-surface-800 transition-all duration-200 text-sm"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Balance cards */}
        <div className="animate-fade-in">
          <BalanceCards balance={balance} />
        </div>

        {/* Tabs */}
        <div className="mt-8 flex gap-1 bg-surface-900/50 p-1 rounded-xl w-fit">
          {[
            { id: 'overview', label: 'Payout & Request' },
            { id: 'ledger', label: 'Ledger History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-surface-800 text-white shadow-md'
                  : 'text-surface-400 hover:text-surface-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="mt-6 animate-slide-up">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1">
                <PayoutForm
                  merchant={merchant}
                  balance={balance}
                  onSuccess={handlePayoutSuccess}
                />
              </div>
              <div className="lg:col-span-2">
                <PayoutHistory payouts={payouts} />
              </div>
            </div>
          )}

          {activeTab === 'ledger' && (
            <LedgerTable entries={ledger} />
          )}
        </div>
      </main>

      {/* Live indicator */}
      <div className="fixed bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 rounded-full
                       bg-surface-900/80 backdrop-blur-sm border border-surface-700/50 text-xs text-surface-400">
        <div className="w-2 h-2 rounded-full bg-accent-500 animate-pulse" />
        Live — auto-refreshing
      </div>
    </div>
  );
}
