import type { TaskStatus, WorkerStatus } from '../types';

interface StatusBadgeProps {
  status: TaskStatus | WorkerStatus;
  size?: 'sm' | 'md';
}

const statusConfig: Record<string, { bg: string; text: string; dot: string }> = {
  // Task statuses
  pending: { bg: 'bg-yellow-500/10', text: 'text-yellow-500', dot: 'bg-yellow-500' },
  processing: { bg: 'bg-blue-500/10', text: 'text-blue-500', dot: 'bg-blue-500' },
  completed: { bg: 'bg-green-500/10', text: 'text-green-500', dot: 'bg-green-500' },
  failed: { bg: 'bg-red-500/10', text: 'text-red-500', dot: 'bg-red-500' },
  // Worker statuses
  idle: { bg: 'bg-green-500/10', text: 'text-green-500', dot: 'bg-green-500' },
  busy: { bg: 'bg-yellow-500/10', text: 'text-yellow-500', dot: 'bg-yellow-500' },
  starting: { bg: 'bg-blue-500/10', text: 'text-blue-500', dot: 'bg-blue-500' },
  stopping: { bg: 'bg-orange-500/10', text: 'text-orange-500', dot: 'bg-orange-500' },
  stopped: { bg: 'bg-gray-500/10', text: 'text-gray-500', dot: 'bg-gray-500' },
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;
  
  const sizeClasses = size === 'sm' 
    ? 'px-2 py-0.5 text-xs' 
    : 'px-2.5 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${sizeClasses}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${config.dot} ${
          status === 'processing' || status === 'busy' ? 'animate-pulse-dot' : ''
        }`}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
