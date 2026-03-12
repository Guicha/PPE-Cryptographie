import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(onEvent) {
  const ws = useRef(null);
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket('ws://localhost:8000/ws');

    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    socket.onerror = () => socket.close();
    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type !== 'heartbeat' && data.type !== 'pong') {
          onEventRef.current(data);
        }
      } catch {}
    };

    ws.current = socket;
  }, []);

  useEffect(() => {
    connect();
    const ping = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send('ping');
      }
    }, 25000);
    return () => {
      clearInterval(ping);
      ws.current?.close();
    };
  }, [connect]);

  return { connected };
}
