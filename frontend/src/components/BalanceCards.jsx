import { Wallet, Lock, TrendingUp, TrendingDown } from 'lucide-react';

function formatPaise(paise) {
  const rupees = Math.abs(paise) / 100;
  return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function BalanceCards({ balance }) {
  if (!balance) return null;

  const cards = [
    {
      label: 'Available Balance',
      value: balance.available_balance_paise,
      formatted: formatPaise(balance.available_balance_paise),
      icon: Wallet,
      gradient: 'from-accent-500/20 to-emerald-500/20',
      iconBg: 'bg-accent-500/20',
      iconColor: 'text-accent-400',
      valueColor: 'gradient-text',
    },
    {
      label: 'Held Balance',
      value: balance.held_balance_paise,
      formatted: formatPaise(balance.held_balance_paise),
      icon: Lock,
      gradient: 'from-amber-500/20 to-orange-500/20',
      iconBg: 'bg-amber-500/20',
      iconColor: 'text-amber-400',
      valueColor: 'gradient-text-amber',
    },
    {
      label: 'Total Credits',
      value: balance.total_credits_paise,
      formatted: formatPaise(balance.total_credits_paise),
      icon: TrendingUp,
      gradient: 'from-blue-500/20 to-cyan-500/20',
      iconBg: 'bg-blue-500/20',
      iconColor: 'text-blue-400',
      valueColor: 'text-blue-400',
    },
    {
      label: 'Total Debits',
      value: balance.total_debits_paise,
      formatted: formatPaise(balance.total_debits_paise),
      icon: TrendingDown,
      gradient: 'from-rose-500/20 to-pink-500/20',
      iconBg: 'bg-rose-500/20',
      iconColor: 'text-rose-400',
      valueColor: 'text-rose-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <div
          key={card.label}
          className="glass-card-hover p-5"
          style={{ animationDelay: `${i * 100}ms` }}
        >
          <div className="flex items-start justify-between mb-4">
            <div className={`p-2.5 rounded-xl ${card.iconBg}`}>
              <card.icon className={`w-5 h-5 ${card.iconColor}`} />
            </div>
          </div>
          <p className="text-xs font-medium text-surface-400 uppercase tracking-wider mb-1">
            {card.label}
          </p>
          <p className={`text-2xl font-bold ${card.valueColor}`}>
            {card.formatted}
          </p>
        </div>
      ))}
    </div>
  );
}
