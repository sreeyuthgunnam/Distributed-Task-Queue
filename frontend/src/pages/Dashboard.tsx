import { useState, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Users,
  Server,
  TrendingUp,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { queuesApi, workersApi } from '../lib/api';
import { useDashboardWebSocket } from '../lib/websocket';
import RealTimeChart, { useChartData } from '../components/RealTimeChart';
import StatusBadge from '../components/StatusBadge';
import type { QueueStats, WSDashboardUpdate } from '../types';

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  trend?: { value: number; label: string };
  color?: string;
}

function StatCard({ title, value, icon, trend, color = 'blue' }: StatCardProps) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-500',
    green: 'bg-green-500/10 text-green-500',
    red: 'bg-red-500/10 text-red-500',
    yellow: 'bg-yellow-500/10 text-yellow-500',
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
          {trend && (
            <div className="flex items-center gap-1 mt-2 text-sm">
              <TrendingUp className="w-4 h-4 text-green-500" />
              <span className="text-green-500">{trend.value}</span>
              <span className="text-gray-500">{trend.label}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

interface QueueCardProps {
  queue: QueueStats;
}

function QueueCard({ queue }: QueueCardProps) {
  const total = queue.pending + queue.processing + queue.completed + queue.failed;
  const successRate = total > 0 ? ((queue.completed / total) * 100).toFixed(1) : '0';

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">{queue.queue_name}</h3>
        {queue.paused && (
          <span className="text-xs bg-yellow-500/10 text-yellow-500 px-2 py-0.5 rounded-full">
            Paused
          </span>
        )}
      </div>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-gray-400">Pending</span>
          <span className="ml-auto font-medium">{queue.pending}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse-dot" />
          <span className="text-gray-400">Processing</span>
          <span className="ml-auto font-medium">{queue.processing}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-gray-400">Completed</span>
          <span className="ml-auto font-medium">{queue.completed}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-gray-400">Failed</span>
          <span className="ml-auto font-medium">{queue.failed}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-dark-700">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Success Rate</span>
          <span className="font-medium text-green-500">{successRate}%</span>
        </div>
        <div className="mt-2 h-2 bg-dark-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all duration-300"
            style={{ width: `${successRate}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState<WSDashboardUpdate | null>(null);
  const throughputChart = useChartData(60);
  const lastThroughputRef = useRef(0);

  // Fetch initial data
  const { data: queuesData } = useQuery({
    queryKey: ['queues'],
    queryFn: queuesApi.list,
    refetchInterval: 5000,
  });

  const { data: workersData } = useQuery({
    queryKey: ['workers'],
    queryFn: workersApi.list,
    refetchInterval: 5000,
  });

  // WebSocket updates
  const handleDashboardUpdate = useCallback((update: WSDashboardUpdate) => {
    setDashboardData(update);
    
    // Calculate throughput (tasks completed since last update)
    const totalCompleted = update.queues.reduce((sum, q) => sum + q.completed, 0);
    const throughput = totalCompleted - lastThroughputRef.current;
    lastThroughputRef.current = totalCompleted;
    
    if (throughput >= 0) {
      throughputChart.addDataPoint(throughput);
    }
  }, [throughputChart]);

  const { connected } = useDashboardWebSocket(handleDashboardUpdate);

  // Use WebSocket data if available, otherwise fall back to REST data
  const queues = dashboardData?.queues || queuesData?.queues || [];
  const workers = dashboardData?.workers || {
    total: workersData?.total_workers || 0,
    active: workersData?.active_workers || 0,
    idle: workersData?.idle_workers || 0,
    busy: workersData?.busy_workers || 0,
  };

  // Calculate totals
  const totalPending = queues.reduce((sum, q) => sum + q.pending, 0);
  const totalProcessing = queues.reduce((sum, q) => sum + q.processing, 0);
  const totalCompleted = queues.reduce((sum, q) => sum + q.completed, 0);
  const totalFailed = queues.reduce((sum, q) => sum + q.failed, 0);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-400 mt-1">Real-time task queue monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-2 text-sm text-green-500">
              <Wifi className="w-4 h-4" />
              Live
            </span>
          ) : (
            <span className="flex items-center gap-2 text-sm text-red-500">
              <WifiOff className="w-4 h-4" />
              Disconnected
            </span>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Pending Tasks"
          value={totalPending}
          icon={<Clock className="w-6 h-6" />}
          color="yellow"
        />
        <StatCard
          title="Processing"
          value={totalProcessing}
          icon={<Activity className="w-6 h-6" />}
          color="blue"
        />
        <StatCard
          title="Completed"
          value={totalCompleted}
          icon={<CheckCircle2 className="w-6 h-6" />}
          color="green"
        />
        <StatCard
          title="Failed"
          value={totalFailed}
          icon={<XCircle className="w-6 h-6" />}
          color="red"
        />
      </div>

      {/* Charts and Workers Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Throughput Chart */}
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-medium mb-4">Task Throughput</h3>
          <RealTimeChart
            data={throughputChart.data}
            color="#3b82f6"
            height={250}
            type="area"
            yAxisLabel="tasks/s"
          />
        </div>

        {/* Workers Summary */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-medium">Workers</h3>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-dark-700 rounded-lg">
              <span className="text-gray-400">Total</span>
              <span className="text-2xl font-bold">{workers.total}</span>
            </div>
            
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-green-500/10 rounded-lg">
                <p className="text-2xl font-bold text-green-500">{workers.idle}</p>
                <p className="text-xs text-gray-400 mt-1">Idle</p>
              </div>
              <div className="text-center p-3 bg-yellow-500/10 rounded-lg">
                <p className="text-2xl font-bold text-yellow-500">{workers.busy}</p>
                <p className="text-xs text-gray-400 mt-1">Busy</p>
              </div>
              <div className="text-center p-3 bg-blue-500/10 rounded-lg">
                <p className="text-2xl font-bold text-blue-500">{workers.active}</p>
                <p className="text-xs text-gray-400 mt-1">Active</p>
              </div>
            </div>

            {workersData?.workers && workersData.workers.length > 0 && (
              <div className="space-y-2 mt-4">
                <p className="text-sm text-gray-400">Recent Activity</p>
                {workersData.workers.slice(0, 3).map((worker) => (
                  <div
                    key={worker.worker_id}
                    className="flex items-center justify-between p-2 bg-dark-700 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          worker.status === 'idle'
                            ? 'bg-green-500'
                            : worker.status === 'busy'
                            ? 'bg-yellow-500 animate-pulse-dot'
                            : 'bg-gray-500'
                        }`}
                      />
                      <span className="text-sm font-mono">{worker.worker_id.slice(0, 12)}</span>
                    </div>
                    <StatusBadge status={worker.status} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Queue Health */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-gray-400" />
          <h2 className="text-lg font-medium">Queue Health</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {queues.map((queue) => (
            <QueueCard key={queue.queue_name} queue={queue} />
          ))}
          {queues.length === 0 && (
            <div className="col-span-full text-center py-8 text-gray-500">
              No queues found. Submit a task to create a queue.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
