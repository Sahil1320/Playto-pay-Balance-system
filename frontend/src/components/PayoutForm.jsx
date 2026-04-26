import { useState } from 'react';
import { createPayout } from '../api/client';
import toast from 'react-hot-toast';
import { Send, IndianRupee, Building2 } from 'lucide-react';

function generateUUID() {
  return crypto.randomUUID();
}

export default function PayoutForm({ merchant, balance, onSuccess }) {
  const [amount, setAmount] = useState('');
  const [selectedBank, setSelectedBank] = useState('');
  const [loading, setLoading] = useState(false);

  const bankAccounts = merchant?.bank_accounts || [];
  const availableRupees = (balance?.available_balance_paise || 0) / 100;

  const handleSubmit = async (e) => {
    e.preventDefault();

    const amountNum = parseFloat(amount);
    if (!amountNum || amountNum <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    if (amountNum < 1) {
      toast.error('Minimum payout is ₹1');
      return;
    }
    if (!selectedBank) {
      toast.error('Select a bank account');
      return;
    }

    const amountPaise = Math.round(amountNum * 100);
    if (amountPaise > (balance?.available_balance_paise || 0)) {
      toast.error('Insufficient balance');
      return;
    }

    setLoading(true);
    const idempotencyKey = generateUUID();

    try {
      const res = await createPayout(
        {
          amount_paise: amountPaise,
          bank_account_id: selectedBank,
        },
        idempotencyKey
      );
      toast.success(`Payout of ₹${amountNum.toLocaleString('en-IN', { minimumFractionDigits: 2 })} initiated!`);
      setAmount('');
      onSuccess();
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || 'Payout failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-accent-500/15">
          <Send className="w-5 h-5 text-accent-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Request Payout</h3>
          <p className="text-xs text-surface-400">Withdraw to your bank account</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Amount */}
        <div>
          <label className="block text-sm font-medium text-surface-300 mb-2">
            Amount (₹)
          </label>
          <div className="relative">
            <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
            <input
              id="payout-amount"
              type="number"
              step="0.01"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input-field pl-11 font-mono"
              placeholder="0.00"
            />
          </div>
          <p className="mt-1.5 text-xs text-surface-500">
            Available: <span className="text-accent-400 font-mono">
              ₹{availableRupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </p>
        </div>

        {/* Bank Account */}
        <div>
          <label className="block text-sm font-medium text-surface-300 mb-2">
            Bank Account
          </label>
          <div className="relative">
            <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
            <select
              id="payout-bank"
              value={selectedBank}
              onChange={(e) => setSelectedBank(e.target.value)}
              className="input-field pl-11 appearance-none cursor-pointer"
            >
              <option value="">Select bank account</option>
              {bankAccounts.map((bank) => (
                <option key={bank.id} value={bank.id}>
                  {bank.account_holder_name} — {bank.masked_account} ({bank.ifsc_code})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Amount preview */}
        {amount && parseFloat(amount) > 0 && (
          <div className="p-3 rounded-xl bg-surface-800/50 border border-surface-700/30">
            <div className="flex justify-between text-sm">
              <span className="text-surface-400">Payout amount</span>
              <span className="text-white font-mono font-medium">
                ₹{parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex justify-between text-sm mt-1">
              <span className="text-surface-400">In paise</span>
              <span className="text-surface-300 font-mono text-xs">
                {Math.round(parseFloat(amount) * 100).toLocaleString()} paise
              </span>
            </div>
          </div>
        )}

        <button
          id="payout-submit"
          type="submit"
          disabled={loading || !amount || !selectedBank}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Send className="w-4 h-4" />
              Request Payout
            </>
          )}
        </button>
      </form>
    </div>
  );
}
