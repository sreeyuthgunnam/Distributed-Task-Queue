// Task types
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Task {
  id: string;
  name: string;
  payload: Record<string, unknown>;
  status: TaskStatus;
  priority: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  retries: number;
  max_retries: number;
}

export interface TaskCreateRequest {
  name: string;
  payload: Record<string, unknown>;
  priority: number;
  queue: string;
  max_retries: number;
}

export interface TaskCreateResponse {
  id: string;
  status: TaskStatus;
  queue: string;
  message: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// Queue types
export interface QueueStats {
  queue_name: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total: number;
  paused: boolean;
}

export interface QueueListResponse {
  queues: QueueStats[];
  total_queues: number;
}

// Worker types
export type WorkerStatus = 'idle' | 'busy' | 'starting' | 'stopping' | 'stopped';

export interface Worker {
  worker_id: string;
  status: WorkerStatus;
  current_task: string | null;
  current_task_name: string | null;
  last_heartbeat: string;
  tasks_completed: number;
  tasks_failed: number;
  started_at: string;
  queues: string[];
}

export interface WorkerListResponse {
  workers: Worker[];
  total_workers: number;
  active_workers: number;
  idle_workers: number;
  busy_workers: number;
}

export interface WorkerStats {
  worker_id: string;
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
  uptime_seconds: number;
  avg_task_duration_ms: number | null;
}

// WebSocket types
export interface WSTaskUpdate {
  event: 'task_update' | 'task_deleted';
  task_id: string;
  status?: TaskStatus;
  result?: Record<string, unknown> | null;
  error?: string | null;
  timestamp: string;
}

export interface WSDashboardUpdate {
  event: 'dashboard_update';
  queues: QueueStats[];
  workers: {
    total: number;
    active: number;
    idle: number;
    busy: number;
  };
  timestamp: string;
}

// Health types
export interface HealthResponse {
  status: string;
  redis_connected: boolean;
  version: string;
}
