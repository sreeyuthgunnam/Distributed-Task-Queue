import { useState } from 'react';
import { X, Send, ChevronDown } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../lib/api';

interface TaskSubmitModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const taskTypes = [
  { name: 'send_email', label: 'Send Email' },
  { name: 'resize_image', label: 'Resize Image' },
  { name: 'process_data', label: 'Process Data' },
];

const defaultPayloads: Record<string, object> = {
  send_email: {
    to: 'user@example.com',
    subject: 'Hello World',
    body: 'This is a test email.',
  },
  resize_image: {
    url: 'https://example.com/image.jpg',
    width: 800,
    height: 600,
  },
  process_data: {
    data: [{ id: 1, value: 100 }, { id: 2, value: 200 }],
    operation: 'transform',
  },
};

export default function TaskSubmitModal({ isOpen, onClose }: TaskSubmitModalProps) {
  const queryClient = useQueryClient();
  const [taskName, setTaskName] = useState('send_email');
  const [payload, setPayload] = useState(JSON.stringify(defaultPayloads.send_email, null, 2));
  const [priority, setPriority] = useState(5);
  const [queue, setQueue] = useState('default');
  const [maxRetries, setMaxRetries] = useState(3);
  const [payloadError, setPayloadError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['queues'] });
      onClose();
      // Reset form
      setTaskName('send_email');
      setPayload(JSON.stringify(defaultPayloads.send_email, null, 2));
      setPriority(5);
      setQueue('default');
      setMaxRetries(3);
    },
  });

  const handleTaskTypeChange = (name: string) => {
    setTaskName(name);
    setPayload(JSON.stringify(defaultPayloads[name] || {}, null, 2));
    setPayloadError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const parsedPayload = JSON.parse(payload);
      setPayloadError(null);
      
      mutation.mutate({
        name: taskName,
        payload: parsedPayload,
        priority,
        queue,
        max_retries: maxRetries,
      });
    } catch (err) {
      setPayloadError('Invalid JSON payload');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-dark-800 rounded-xl border border-dark-700 w-full max-w-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
            <h2 className="text-lg font-semibold">Submit New Task</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-dark-700 text-gray-400 hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {/* Task Type */}
            <div>
              <label className="label">Task Type</label>
              <div className="relative">
                <select
                  value={taskName}
                  onChange={(e) => handleTaskTypeChange(e.target.value)}
                  className="input w-full appearance-none pr-10"
                >
                  {taskTypes.map((type) => (
                    <option key={type.name} value={type.name}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
              </div>
            </div>

            {/* Queue */}
            <div>
              <label className="label">Queue</label>
              <input
                type="text"
                value={queue}
                onChange={(e) => setQueue(e.target.value)}
                className="input w-full"
                placeholder="default"
              />
            </div>

            {/* Priority */}
            <div>
              <label className="label">Priority: {priority}</label>
              <input
                type="range"
                min="1"
                max="10"
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value))}
                className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Low (1)</span>
                <span>Normal (5)</span>
                <span>High (10)</span>
              </div>
            </div>

            {/* Max Retries */}
            <div>
              <label className="label">Max Retries</label>
              <input
                type="number"
                min="0"
                max="10"
                value={maxRetries}
                onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                className="input w-24"
              />
            </div>

            {/* Payload */}
            <div>
              <label className="label">Payload (JSON)</label>
              <textarea
                value={payload}
                onChange={(e) => {
                  setPayload(e.target.value);
                  setPayloadError(null);
                }}
                rows={8}
                className={`input w-full font-mono text-sm ${
                  payloadError ? 'border-red-500 focus:ring-red-500' : ''
                }`}
              />
              {payloadError && (
                <p className="mt-1 text-sm text-red-500">{payloadError}</p>
              )}
            </div>

            {/* Error message */}
            {mutation.isError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {mutation.error instanceof Error ? mutation.error.message : 'Failed to submit task'}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="btn btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {mutation.isPending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Submit Task
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
