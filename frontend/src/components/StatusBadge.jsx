import { CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';

const STATUS_CONFIG = {
  pending: {
    className: 'status-pending',
    icon: Clock,
    label: 'Pending',
  },
  processing: {
    className: 'status-processing',
    icon: Loader2,
    label: 'Processing',
    animate: true,
  },
  completed: {
    className: 'status-completed',
    icon: CheckCircle,
    label: 'Completed',
  },
  failed: {
    className: 'status-failed',
    icon: XCircle,
    label: 'Failed',
  },
};

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = config.icon;

  return (
    <span className={config.className}>
      <Icon className={`w-3.5 h-3.5 mr-1.5 ${config.animate ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
}
