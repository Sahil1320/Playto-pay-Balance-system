import { BookOpen, ArrowUpRight, ArrowDownLeft, Lock, Unlock } from 'lucide-react';

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
    second: '2-digit',
  });
}

const ENTRY_META = {
  credit: {
    icon: ArrowDownLeft,
    color: 'text-accent-400',
    bg: 'bg-accent-500/15',
    label: 'Credit',
    sign: '+',
  },
  debit: {
    icon: ArrowUpRight,
    color: 'text-rose-400',
    bg: 'bg-rose-500/15',
    label: 'Debit',
    sign: '-',
  },
  hold: {
    icon: Lock,
    color: 'text-amber-400',
    bg: 'bg-amber-500/15',
    label: 'Hold',
    sign: '-',
  },
  release: {
    icon: Unlock,
    color: 'text-blue-400',
    bg: 'bg-blue-500/15',
    label: 'Release',
    sign: '+',
  },
};

export default function LedgerTable({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <BookOpen className="w-12 h-12 text-surface-600 mx-auto mb-3" />
        <p className="text-surface-400 text-sm">No ledger entries yet</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-surface-700/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-500/15">
            <BookOpen className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Ledger History</h3>
            <p className="text-xs text-surface-400">All credits, debits, holds, and releases</p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-800/80">
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Type
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Description
              </th>
              <th className="text-right px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Amount
              </th>
              <th className="text-right px-6 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider">
                Date
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800/50">
            {entries.map((entry) => {
              const meta = ENTRY_META[entry.entry_type] || ENTRY_META.credit;
              const Icon = meta.icon;

              return (
                <tr
                  key={entry.id}
                  className="hover:bg-surface-800/30 transition-colors duration-150"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-1.5 rounded-lg ${meta.bg}`}>
                        <Icon className={`w-4 h-4 ${meta.color}`} />
                      </div>
                      <span className={`text-xs font-semibold uppercase tracking-wider ${meta.color}`}>
                        {meta.label}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-surface-300">{entry.description}</p>
                    {entry.reference_id && (
                      <p className="text-xs text-surface-600 font-mono mt-0.5">
                        ref: {entry.reference_id.slice(0, 8)}
                      </p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`font-mono font-semibold ${meta.color}`}>
                      {meta.sign}{formatPaise(entry.amount_paise)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="text-xs text-surface-400">
                      {formatDate(entry.created_at)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
