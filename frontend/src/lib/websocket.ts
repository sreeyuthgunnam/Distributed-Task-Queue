import { useEffect, useRef, useState } from 'react';
import type { WSDashboardUpdate, WSTaskUpdate } from '../types';

// Use the same host/port as the page, connecting through nginx proxy
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_BASE_URL = `${WS_PROTOCOL}//${window.location.host}/api`;

export function useTaskWebSocket(
  taskId: string | null,
  onUpdate: (update: WSTaskUpdate) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const onUpdateRef = useRef(onUpdate);
  
  // Keep the callback ref updated without causing reconnection
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws/tasks/${taskId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSTaskUpdate;
        onUpdateRef.current(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [taskId]);

  return { connected };
}

export function useDashboardWebSocket(
  onUpdate: (update: WSDashboardUpdate) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const onUpdateRef = useRef(onUpdate);
  const mountedRef = useRef(true);

  // Keep the callback ref updated without causing reconnection
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    mountedRef.current = true;
    
    const connect = () => {
      if (!mountedRef.current) return;
      
      try {
        const ws = new WebSocket(`${WS_BASE_URL}/ws/dashboard`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (mountedRef.current) {
            setConnected(true);
            console.log('Dashboard WebSocket connected');
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as WSDashboardUpdate;
            onUpdateRef.current(data);
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          if (mountedRef.current) {
            setConnected(false);
            console.log('Dashboard WebSocket disconnected, reconnecting...');
            // Reconnect after 3 seconds
            reconnectTimeoutRef.current = setTimeout(connect, 3000);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      } catch (e) {
        console.error('Failed to create WebSocket:', e);
        if (mountedRef.current) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // Empty dependency array - only run once on mount

  return { connected };
}
