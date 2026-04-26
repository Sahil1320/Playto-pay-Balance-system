import StatusBadge from './StatusBadge';
import { ArrowDownRight, Clock, Hash } from 'lucide-react';

function formatPaise(paise) {
  const rupees = paise / 100;
  return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatTimeAgo(dateStr) {
  const seconds = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PayoutHistory({ payouts }) {
  if (!payouts || payouts.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <ArrowDownRight className="w-12 h-12 text-surface-600 mx-auto mb-3" />
        <p className="text-surface-400 text-sm">No payouts yet</p>
        <p className="text-surface-600 text-xs mt-1">Request your first payout to see it here</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-surface-700/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/15">
            <Clock className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Payout History</h3>
            <p className="text-xs text-surface-400">{payouts.length} recent payouts</p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-800/80">
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                ID
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Amount
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Status
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Bank Account
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Attempts
              </th>
              <th className="text-right px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800/50">
            {payouts.map((payout) => (
              <tr
                key={payout.id}
                className="hover:bg-surface-800/30 transition-colors duration-150"
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1.5">
                    <Hash className="w-3 h-3 text-surface-600" />
                    <span className="font-mono text-xs text-surface-300">
                      {payout.id.slice(0, 8)}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="font-mono font-semibold text-white">
                    {formatPaise(payout.amount_paise)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={payout.status} />
                </td>
                <td className="px-6 py-4">
                  <span className="text-sm text-surface-400">
                    {payout.bank_account_detail?.masked_account || '—'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className="text-sm text-surface-400">{payout.attempts}/3</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <div>
                    <p className="text-xs text-surface-400">{formatDate(payout.created_at)}</p>
                    <p className="text-xs text-surface-600">{formatTimeAgo(payout.created_at)}</p>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
