import { useState } from 'react';
import { login } from '../api/client';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Lock, User, ArrowRight, Zap } from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error('Please enter username and password');
      return;
    }

    setLoading(true);
    try {
      await login(username, password);
      toast.success('Welcome back!');
      onLoginSuccess();
      navigate('/');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid credentials';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (user) => {
    setUsername(user);
    setPassword('testpass123');
    setLoading(true);
    try {
      await login(user, 'testpass123');
      toast.success(`Logged in as ${user}`);
      onLoginSuccess();
      navigate('/');
    } catch (err) {
      toast.error('Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-surface-950 via-surface-900 to-surface-950" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo and header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-500 to-emerald-500 mb-4 shadow-lg shadow-accent-500/25">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Playto Pay</h1>
          <p className="text-surface-400 text-sm">Merchant Payout Dashboard</p>
        </div>

        {/* Login card */}
        <div className="glass-card p-8 animate-slide-up">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-field pl-11"
                  placeholder="Enter your username"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-11"
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick login buttons */}
          <div className="mt-8 pt-6 border-t border-surface-700/50">
            <p className="text-xs text-surface-500 text-center mb-4 uppercase tracking-wider font-medium">
              Quick Login — Test Accounts
            </p>
            <div className="space-y-2">
              {[
                { user: 'acme', label: 'Acme Design Studio', balance: '₹2,50,000' },
                { user: 'pixelforge', label: 'Pixel Forge Labs', balance: '₹1,00,000' },
                { user: 'cloudnine', label: 'Cloud Nine Agency', balance: '₹50,000' },
              ].map(({ user, label, balance }) => (
                <button
                  key={user}
                  onClick={() => quickLogin(user)}
                  disabled={loading}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-surface-800/60
                             border border-surface-700/40 hover:bg-surface-700/60 hover:border-surface-600
                             transition-all duration-200 group"
                >
                  <div className="text-left">
                    <p className="text-sm font-medium text-surface-200 group-hover:text-white transition-colors">{label}</p>
                    <p className="text-xs text-surface-500">{user} / testpass123</p>
                  </div>
                  <span className="text-xs font-mono text-accent-400">{balance}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
