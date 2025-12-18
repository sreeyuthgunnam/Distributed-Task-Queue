const API_BASE_URL = '/api';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
  return response.json();
}

// Tasks API
export const tasksApi = {
  list: async (params?: {
    status?: string;
    queue?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.queue) searchParams.set('queue', params.queue);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    
    const response = await fetch(`${API_BASE_URL}/tasks?${searchParams}`);
    return handleResponse<import('../types').TaskListResponse>(response);
  },

  get: async (taskId: string) => {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
    return handleResponse<import('../types').Task>(response);
  },

  create: async (data: import('../types').TaskCreateRequest) => {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<import('../types').TaskCreateResponse>(response);
  },

  cancel: async (taskId: string, queue = 'default') => {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}?queue=${queue}`, {
      method: 'DELETE',
    });
    return handleResponse<{ id: string; cancelled: boolean; message: string }>(response);
  },

  retry: async (taskId: string, queue = 'default') => {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/retry?queue=${queue}`, {
      method: 'POST',
    });
    return handleResponse<{ id: string; retried: boolean; retry_count: number; message: string }>(response);
  },
};

// Queues API
export const queuesApi = {
  list: async () => {
    const response = await fetch(`${API_BASE_URL}/queues`);
    return handleResponse<import('../types').QueueListResponse>(response);
  },

  getStats: async (queueName: string) => {
    const response = await fetch(`${API_BASE_URL}/queues/${queueName}/stats`);
    return handleResponse<import('../types').QueueStats>(response);
  },

  pause: async (queueName: string) => {
    const response = await fetch(`${API_BASE_URL}/queues/${queueName}/pause`, {
      method: 'POST',
    });
    return handleResponse<{ queue_name: string; action: string; success: boolean; message: string }>(response);
  },

  resume: async (queueName: string) => {
    const response = await fetch(`${API_BASE_URL}/queues/${queueName}/resume`, {
      method: 'POST',
    });
    return handleResponse<{ queue_name: string; action: string; success: boolean; message: string }>(response);
  },

  clearDeadLetter: async (queueName: string) => {
    const response = await fetch(`${API_BASE_URL}/queues/${queueName}/dead-letter`, {
      method: 'DELETE',
    });
    return handleResponse<{ queue_name: string; cleared_count: number; message: string }>(response);
  },
};

// Workers API
export const workersApi = {
  list: async () => {
    const response = await fetch(`${API_BASE_URL}/workers`);
    return handleResponse<import('../types').WorkerListResponse>(response);
  },

  get: async (workerId: string) => {
    const response = await fetch(`${API_BASE_URL}/workers/${workerId}`);
    return handleResponse<import('../types').Worker>(response);
  },

  getStats: async (workerId: string) => {
    const response = await fetch(`${API_BASE_URL}/workers/${workerId}/stats`);
    return handleResponse<import('../types').WorkerStats>(response);
  },
};

// Health API
export const healthApi = {
  check: async () => {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<import('../types').HealthResponse>(response);
  },
};
