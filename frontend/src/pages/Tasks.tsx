import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Plus,
  Search,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { tasksApi } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import TaskSubmitModal from '../components/TaskSubmitModal';
import TaskDetailPanel from '../components/TaskDetailPanel';
import type { TaskStatus } from '../types';

const statusOptions: { value: TaskStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(startStr: string | null, endStr: string | null): string {
  if (!startStr) return '-';
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  const ms = end - start;
  
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export default function Tasks() {
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('');
  const [queueFilter, setQueueFilter] = useState('default');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['tasks', statusFilter, queueFilter, page],
    queryFn: () =>
      tasksApi.list({
        status: statusFilter || undefined,
        queue: queueFilter,
        limit,
        offset: page * limit,
      }),
    refetchInterval: 5000,
  });

  const tasks = data?.tasks || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit);

  // Filter by search query (client-side)
  const filteredTasks = searchQuery
    ? tasks.filter(
        (task) =>
          task.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          task.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : tasks;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Tasks</h1>
          <p className="text-gray-400 mt-1">Manage and monitor task execution</p>
        </div>
        <button
          onClick={() => setShowSubmitModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Submit Task
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by ID or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input w-full pl-10"
          />
        </div>

        {/* Status Filter */}
        <div className="relative">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as TaskStatus | '');
              setPage(0);
            }}
            className="input appearance-none pr-10 min-w-[150px]"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>

        {/* Queue Filter */}
        <div className="relative">
          <input
            type="text"
            placeholder="Queue name"
            value={queueFilter}
            onChange={(e) => {
              setQueueFilter(e.target.value);
              setPage(0);
            }}
            className="input min-w-[150px]"
          />
        </div>

        {/* Refresh */}
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-700">
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">ID</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">Name</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">Status</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">Priority</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">Created</th>
                <th className="text-left py-4 px-6 text-sm font-medium text-gray-400">Duration</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="flex items-center justify-center gap-3 text-gray-500">
                      <div className="w-5 h-5 border-2 border-gray-500/30 border-t-gray-500 rounded-full animate-spin" />
                      Loading tasks...
                    </div>
                  </td>
                </tr>
              ) : filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-gray-500">
                    No tasks found
                  </td>
                </tr>
              ) : (
                filteredTasks.map((task) => (
                  <tr
                    key={task.id}
                    onClick={() => setSelectedTaskId(task.id)}
                    className="border-b border-dark-700 hover:bg-dark-700/50 cursor-pointer transition-colors"
                  >
                    <td className="py-4 px-6">
                      <code className="text-sm text-gray-300 font-mono">
                        {task.id.slice(0, 8)}...
                      </code>
                    </td>
                    <td className="py-4 px-6">
                      <span className="font-medium">{task.name}</span>
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={task.status} size="sm" />
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-dark-600 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${task.priority * 10}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-400">{task.priority}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-sm text-gray-400">
                      {formatDate(task.created_at)}
                    </td>
                    <td className="py-4 px-6 text-sm text-gray-400">
                      {formatDuration(task.started_at, task.completed_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-dark-700">
            <p className="text-sm text-gray-400">
              Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total} tasks
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn btn-secondary py-1.5 px-2 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-400 px-2">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn btn-secondary py-1.5 px-2 disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Submit Modal */}
      <TaskSubmitModal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
      />

      {/* Detail Panel */}
      <TaskDetailPanel
        taskId={selectedTaskId}
        onClose={() => setSelectedTaskId(null)}
      />
    </div>
  );
}
