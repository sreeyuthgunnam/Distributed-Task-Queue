import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Server,
  Pause,
  Play,
  Trash2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { queuesApi } from '../lib/api';
import type { QueueStats } from '../types';

function QueueCard({ queue }: { queue: QueueStats }) {
  const queryClient = useQueryClient();

  const pauseMutation = useMutation({
    mutationFn: () => queuesApi.pause(queue.queue_name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queues'] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => queuesApi.resume(queue.queue_name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queues'] });
    },
  });

  const total = queue.pending + queue.processing + queue.completed + queue.failed;
  const successRate = total > 0 ? ((queue.completed / total) * 100).toFixed(1) : '100';
  const failureRate = total > 0 ? ((queue.failed / total) * 100).toFixed(1) : '0';

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <Server className="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <h3 className="font-semibold">{queue.queue_name}</h3>
            <p className="text-sm text-gray-500">{total} total tasks</p>
          </div>
        </div>
        {queue.paused ? (
          <button
            onClick={() => resumeMutation.mutate()}
            disabled={resumeMutation.isPending}
            className="btn btn-success text-sm py-1.5 flex items-center gap-1.5"
          >
            <Play className="w-4 h-4" />
            Resume
          </button>
        ) : (
          <button
            onClick={() => pauseMutation.mutate()}
            disabled={pauseMutation.isPending}
            className="btn btn-secondary text-sm py-1.5 flex items-center gap-1.5"
          >
            <Pause className="w-4 h-4" />
            Pause
          </button>
        )}
      </div>

      {/* Status indicator */}
      {queue.paused && (
        <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-yellow-500" />
          <span className="text-sm text-yellow-500">Queue is paused - workers will not pick up new tasks</span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-sm text-gray-400">Pending</span>
          </div>
          <p className="text-2xl font-bold">{queue.pending}</p>
        </div>
        <div className="bg-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse-dot" />
            <span className="text-sm text-gray-400">Processing</span>
          </div>
          <p className="text-2xl font-bold">{queue.processing}</p>
        </div>
        <div className="bg-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-sm text-gray-400">Completed</span>
          </div>
          <p className="text-2xl font-bold">{queue.completed}</p>
        </div>
        <div className="bg-dark-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-sm text-gray-400">Failed</span>
          </div>
          <p className="text-2xl font-bold">{queue.failed}</p>
        </div>
      </div>

      {/* Progress Bars */}
      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-400">Success Rate</span>
            <span className="text-green-500 font-medium">{successRate}%</span>
          </div>
          <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-500"
              style={{ width: `${successRate}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-400">Failure Rate</span>
            <span className="text-red-500 font-medium">{failureRate}%</span>
          </div>
          <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-red-500 rounded-full transition-all duration-500"
              style={{ width: `${failureRate}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function DeadLetterQueueCard({ queueName }: { queueName: string }) {
  const queryClient = useQueryClient();

  const clearMutation = useMutation({
    mutationFn: () => queuesApi.clearDeadLetter(queueName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queues'] });
    },
  });

  return (
    <div className="card border-red-500/20">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-500/10 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <div>
            <h3 className="font-semibold">{queueName}:dlq</h3>
            <p className="text-sm text-gray-500">Dead Letter Queue</p>
          </div>
        </div>
      </div>

      <p className="text-sm text-gray-400 mb-4">
        Tasks that have exceeded their maximum retry attempts are moved here.
        You can retry them individually or clear the queue.
      </p>

      <div className="flex gap-3">
        <button
          onClick={() => clearMutation.mutate()}
          disabled={clearMutation.isPending}
          className="btn btn-danger text-sm flex items-center gap-1.5"
        >
          <Trash2 className="w-4 h-4" />
          {clearMutation.isPending ? 'Clearing...' : 'Clear DLQ'}
        </button>
      </div>

      {clearMutation.isSuccess && (
        <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-sm text-green-400">
          Dead letter queue cleared successfully
        </div>
      )}
    </div>
  );
}

export default function Queues() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['queues'],
    queryFn: queuesApi.list,
    refetchInterval: 5000,
  });

  const queues = data?.queues || [];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Queues</h1>
          <p className="text-gray-400 mt-1">Manage task queues and dead letter queues</p>
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

      {/* Queues Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-gray-500">
            <div className="w-6 h-6 border-2 border-gray-500/30 border-t-gray-500 rounded-full animate-spin" />
            Loading queues...
          </div>
        </div>
      ) : queues.length === 0 ? (
        <div className="card text-center py-12">
          <Server className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400 mb-2">No Queues Found</h3>
          <p className="text-gray-500">Submit a task to create a queue automatically.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {queues.map((queue) => (
              <QueueCard key={queue.queue_name} queue={queue} />
            ))}
          </div>

          {/* Dead Letter Queues */}
          <div className="mb-8">
            <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Dead Letter Queues
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {queues.map((queue) => (
                <DeadLetterQueueCard key={queue.queue_name} queueName={queue.queue_name} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
