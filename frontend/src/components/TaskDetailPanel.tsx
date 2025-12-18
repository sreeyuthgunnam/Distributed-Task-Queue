import { useCallback, useEffect, useState } from 'react';
import { X, Clock, RefreshCw, Copy, Check } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../lib/api';
import { useTaskWebSocket } from '../lib/websocket';
import StatusBadge from './StatusBadge';
import type { Task, WSTaskUpdate } from '../types';

interface TaskDetailPanelProps {
  taskId: string | null;
  onClose: () => void;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded hover:bg-dark-600 text-gray-500 hover:text-gray-300"
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
    </button>
  );
}

export default function TaskDetailPanel({ taskId, onClose }: TaskDetailPanelProps) {
  const queryClient = useQueryClient();
  const [task, setTask] = useState<Task | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => tasksApi.get(taskId!),
    enabled: !!taskId,
  });

  useEffect(() => {
    if (data) {
      setTask(data);
    }
  }, [data]);

  const handleWSUpdate = useCallback((update: WSTaskUpdate) => {
    if (update.event === 'task_update' && task) {
      setTask((prev) => prev ? {
        ...prev,
        status: update.status!,
        result: update.result ?? prev.result,
        error: update.error ?? prev.error,
      } : null);
    }
  }, [task]);

  useTaskWebSocket(taskId, handleWSUpdate);

  const retryMutation = useMutation({
    mutationFn: () => tasksApi.retry(taskId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => tasksApi.cancel(taskId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  if (!taskId) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[500px] bg-dark-800 border-l border-dark-700 shadow-xl z-40 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
        <h2 className="text-lg font-semibold">Task Details</h2>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-dark-700 text-gray-400 hover:text-gray-200"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : task ? (
          <div className="space-y-6">
            {/* Status and Actions */}
            <div className="flex items-center justify-between">
              <StatusBadge status={task.status} />
              <div className="flex gap-2">
                {task.status === 'pending' && (
                  <button
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="btn btn-danger text-sm py-1.5"
                  >
                    Cancel
                  </button>
                )}
                {task.status === 'failed' && task.retries < task.max_retries && (
                  <button
                    onClick={() => retryMutation.mutate()}
                    disabled={retryMutation.isPending}
                    className="btn btn-primary text-sm py-1.5 flex items-center gap-1.5"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry
                  </button>
                )}
              </div>
            </div>

            {/* Task Info */}
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Task ID</label>
                <div className="flex items-center gap-2 mt-1">
                  <code className="text-sm font-mono text-gray-300 bg-dark-700 px-2 py-1 rounded">
                    {task.id}
                  </code>
                  <CopyButton text={task.id} />
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Name</label>
                <p className="text-gray-200 mt-1">{task.name}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider">Priority</label>
                  <p className="text-gray-200 mt-1">{task.priority}/10</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider">Retries</label>
                  <p className="text-gray-200 mt-1">{task.retries}/{task.max_retries}</p>
                </div>
              </div>
            </div>

            {/* Timing */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Timing
              </h3>
              <div className="bg-dark-700 rounded-lg p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Created</span>
                  <span className="text-gray-200">{formatDate(task.created_at)}</span>
                </div>
                {task.started_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Started</span>
                    <span className="text-gray-200">{formatDate(task.started_at)}</span>
                  </div>
                )}
                {task.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Completed</span>
                    <span className="text-gray-200">{formatDate(task.completed_at)}</span>
                  </div>
                )}
                {task.started_at && task.completed_at && (
                  <div className="flex justify-between pt-2 border-t border-dark-600">
                    <span className="text-gray-400">Duration</span>
                    <span className="text-gray-200">
                      {formatDuration(
                        new Date(task.completed_at).getTime() - new Date(task.started_at).getTime()
                      )}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Payload */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-400">Payload</h3>
                <CopyButton text={JSON.stringify(task.payload, null, 2)} />
              </div>
              <pre className="bg-dark-700 rounded-lg p-4 text-sm font-mono text-gray-300 overflow-x-auto">
                {JSON.stringify(task.payload, null, 2)}
              </pre>
            </div>

            {/* Result */}
            {task.result && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-green-400">Result</h3>
                  <CopyButton text={JSON.stringify(task.result, null, 2)} />
                </div>
                <pre className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-sm font-mono text-green-300 overflow-x-auto">
                  {JSON.stringify(task.result, null, 2)}
                </pre>
              </div>
            )}

            {/* Error */}
            {task.error && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-red-400">Error</h3>
                <pre className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-sm font-mono text-red-300 overflow-x-auto whitespace-pre-wrap">
                  {task.error}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            Task not found
          </div>
        )}
      </div>
    </div>
  );
}
