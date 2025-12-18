import { useQuery } from '@tanstack/react-query';
import {
  Users,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { workersApi } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import type { Worker } from '../types';

function formatUptime(startedAt: string): string {
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  const seconds = Math.floor((now - start) / 1000);

  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

function formatLastSeen(lastHeartbeat: string): string {
  const last = new Date(lastHeartbeat).getTime();
  const now = Date.now();
  const seconds = Math.floor((now - last) / 1000);

  if (seconds < 5) return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function WorkerCard({ worker }: { worker: Worker }) {
  const lastSeenSeconds = Math.floor(
    (Date.now() - new Date(worker.last_heartbeat).getTime()) / 1000
  );
  const isStale = lastSeenSeconds > 30;

  const successRate =
    worker.tasks_completed + worker.tasks_failed > 0
      ? ((worker.tasks_completed / (worker.tasks_completed + worker.tasks_failed)) * 100).toFixed(1)
      : '100';

  return (
    <div className={`card ${isStale ? 'border-red-500/30' : ''}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg ${
              isStale
                ? 'bg-red-500/10'
                : worker.status === 'busy'
                ? 'bg-yellow-500/10'
                : 'bg-green-500/10'
            }`}
          >
            <Users
              className={`w-5 h-5 ${
                isStale
                  ? 'text-red-500'
                  : worker.status === 'busy'
                  ? 'text-yellow-500'
                  : 'text-green-500'
              }`}
            />
          </div>
          <div>
            <h3 className="font-semibold font-mono">{worker.worker_id}</h3>
            <p className="text-sm text-gray-500">
              {worker.queues.join(', ')}
            </p>
          </div>
        </div>
        <StatusBadge status={isStale ? 'stopped' : worker.status} />
      </div>

      {/* Stale Warning */}
      {isStale && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2">
          <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="text-sm text-red-400">
            Worker appears to be offline (no heartbeat for {lastSeenSeconds}s)
          </span>
        </div>
      )}

      {/* Current Task */}
      {worker.current_task && (
        <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-blue-500" />
            <span className="text-sm text-blue-400">Currently Processing</span>
          </div>
          <p className="text-sm font-mono text-gray-300 truncate">
            {worker.current_task_name || worker.current_task}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-dark-700 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-400 mb-1">
            <Clock className="w-4 h-4" />
            <span className="text-xs">Uptime</span>
          </div>
          <p className="font-semibold">{formatUptime(worker.started_at)}</p>
        </div>
        <div className="bg-dark-700 rounded-lg p-3">
          <div className="flex items-center gap-2 text-gray-400 mb-1">
            <Activity className="w-4 h-4" />
            <span className="text-xs">Last Seen</span>
          </div>
          <p className={`font-semibold ${isStale ? 'text-red-400' : ''}`}>
            {formatLastSeen(worker.last_heartbeat)}
          </p>
        </div>
      </div>

      {/* Task Counts */}
      <div className="flex items-center gap-4 p-3 bg-dark-700 rounded-lg">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          <span className="text-sm text-gray-400">Completed</span>
          <span className="font-semibold text-green-500">{worker.tasks_completed}</span>
        </div>
        <div className="flex items-center gap-2">
          <XCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm text-gray-400">Failed</span>
          <span className="font-semibold text-red-500">{worker.tasks_failed}</span>
        </div>
      </div>

      {/* Success Rate */}
      <div className="mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-400">Success Rate</span>
          <span className="font-medium text-green-500">{successRate}%</span>
        </div>
        <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all duration-500"
            style={{ width: `${successRate}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default function Workers() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['workers'],
    queryFn: workersApi.list,
    refetchInterval: 5000,
  });

  const workers = data?.workers || [];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Workers</h1>
          <p className="text-gray-400 mt-1">Monitor worker health and performance</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="card bg-dark-700">
            <p className="text-sm text-gray-400 mb-1">Total Workers</p>
            <p className="text-3xl font-bold">{data.total_workers}</p>
          </div>
          <div className="card bg-blue-500/10 border-blue-500/20">
            <p className="text-sm text-blue-400 mb-1">Active</p>
            <p className="text-3xl font-bold text-blue-500">{data.active_workers}</p>
          </div>
          <div className="card bg-green-500/10 border-green-500/20">
            <p className="text-sm text-green-400 mb-1">Idle</p>
            <p className="text-3xl font-bold text-green-500">{data.idle_workers}</p>
          </div>
          <div className="card bg-yellow-500/10 border-yellow-500/20">
            <p className="text-sm text-yellow-400 mb-1">Busy</p>
            <p className="text-3xl font-bold text-yellow-500">{data.busy_workers}</p>
          </div>
        </div>
      )}

      {/* Workers Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-gray-500">
            <div className="w-6 h-6 border-2 border-gray-500/30 border-t-gray-500 rounded-full animate-spin" />
            Loading workers...
          </div>
        </div>
      ) : workers.length === 0 ? (
        <div className="card text-center py-12">
          <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400 mb-2">No Workers Found</h3>
          <p className="text-gray-500 mb-4">
            Start a worker to begin processing tasks.
          </p>
          <div className="bg-dark-700 rounded-lg p-4 max-w-md mx-auto">
            <p className="text-sm text-gray-400 mb-2">Run this command to start a worker:</p>
            <code className="text-sm text-blue-400 font-mono">
              python -m src.worker.main --worker-id worker-1 --queues default
            </code>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {workers.map((worker) => (
            <WorkerCard key={worker.worker_id} worker={worker} />
          ))}
        </div>
      )}
    </div>
  );
}
