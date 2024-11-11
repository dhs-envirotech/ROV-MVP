import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Power, Clock } from 'lucide-react';

const App = () => {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const [power, setPower] = useState(100);
  const [activeKeys, setActiveKeys] = useState(new Set());
  const [metrics, setMetrics] = useState({ fps: 0, latency: 0 });
  const [commandHistory, setCommandHistory] = useState([]);
  
  // Refs for continuous movement
  const moveIntervalRef = useRef(null);
  const activeCommandRef = useRef(null);

  // Connect/reconnect function
  const connectWebSocket = useCallback(() => {
    try {
      if (ws) {
        ws.close();
      }

      const socket = new WebSocket('ws://127.0.0.1:5000/ws');

      socket.onopen = () => {
        console.log('Connected to server');
        setConnected(true);
        socket.send(JSON.stringify({
          type: 'start_video',
          data: {}
        }));
      };

      socket.onclose = () => {
        console.log('Disconnected from server');
        setConnected(false);
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      };

      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === 'connection_status') {
          setConnected(message.data.status === 'connected');
        }
        else if (message.type === 'video_frame') {
          setVideoStream(`data:image/jpeg;base64,${message.data.frame}`);
          const latency = (Date.now() - message.data.timestamp * 1000).toFixed(1);
          setMetrics(prev => ({
            fps: message.data.fps || prev.fps,
            latency
          }));
        } else if (message.type === 'command_response') {
          const latency = (Date.now() - message.data.timestamp * 1000).toFixed(1);
          setCommandHistory(prev => [{
            command: message.data.command,
            power: message.data.power,
            latency,
            timestamp: new Date().toLocaleTimeString()
          }, ...prev].slice(0, 5));
        }
      };

      setWs(socket);
    } catch (error) {
      console.error('Connection error:', error);
      setConnected(false);
      // Try to reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    }
  }, []);

  // Initial connection
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (moveIntervalRef.current) {
        clearInterval(moveIntervalRef.current);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [connectWebSocket]);

  // Handle power changes
  const handlePowerChange = (newPower) => {
    setPower(newPower);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'power_update',
        data: { power: newPower }
      }));
    }
  };

  // Movement command handler
  const sendCommand = useCallback((command) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'movement_command',
        data: { command, power }
      }));
    }
  }, [ws, power]);

  // Start continuous movement
  const startContinuousMove = useCallback((command) => {
    if (moveIntervalRef.current) {
      clearInterval(moveIntervalRef.current);
    }
    
    activeCommandRef.current = command;
    sendCommand(command); // Send initial command
    
    // Send command every 100ms while key is held
    moveIntervalRef.current = setInterval(() => {
      if (activeCommandRef.current === command) {
        sendCommand(command);
      }
    }, 100);
  }, [sendCommand]);

  // Stop continuous movement
  const stopContinuousMove = useCallback((command) => {
    if (activeCommandRef.current === command) {
      clearInterval(moveIntervalRef.current);
      moveIntervalRef.current = null;
      activeCommandRef.current = null;
    }
  }, []);

  // Keyboard controls
  useEffect(() => {
    const keyMap = {
      'ArrowUp': 'forward',
      'ArrowDown': 'backward',
      'ArrowLeft': 'left',
      'ArrowRight': 'right'
    };

    const handleKeyDown = (e) => {
      const command = keyMap[e.key];
      if (command && !activeKeys.has(e.key)) {
        setActiveKeys(prev => new Set(prev).add(e.key));
        startContinuousMove(command);
      }
    };

    const handleKeyUp = (e) => {
      const command = keyMap[e.key];
      if (command) {
        setActiveKeys(prev => {
          const next = new Set(prev);
          next.delete(e.key);
          return next;
        });
        stopContinuousMove(command);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      if (moveIntervalRef.current) {
        clearInterval(moveIntervalRef.current);
      }
    };
  }, [startContinuousMove, stopContinuousMove, activeKeys]);

  // Update mouse/touch handlers for buttons
  const handleButtonPress = (command) => {
    setActiveKeys(prev => new Set(prev).add(command));
    startContinuousMove(command);
  };

  const handleButtonRelease = (command) => {
    setActiveKeys(prev => {
      const next = new Set(prev);
      next.delete(command);
      return next;
    });
    stopContinuousMove(command);
  };

  return (
    <div className="container mx-auto p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Video Feed */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden">
            {videoStream ? (
              <img 
                src={videoStream} 
                alt="Robot camera feed" 
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-white">
                {connected ? 'Waiting for video...' : 'Connecting to server...'}
              </div>
            )}
            {/* Metrics Overlay */}
            <div className="absolute top-2 left-2 text-white text-sm bg-black bg-opacity-50 p-2 rounded">
              <div>FPS: {metrics.fps}</div>
              <div>Latency: {metrics.latency}ms</div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Controls */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="grid grid-cols-3 gap-2 max-w-[240px] mx-auto">
              <div className="col-start-2">
                <button
                  className={`w-full p-4 rounded-lg ${
                    activeKeys.has('ArrowUp') 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                  onMouseDown={() => handleButtonPress('forward')}
                  onMouseUp={() => handleButtonRelease('forward')}
                  onMouseLeave={() => handleButtonRelease('forward')}
                  onTouchStart={() => handleButtonPress('forward')}
                  onTouchEnd={() => handleButtonRelease('forward')}
                >
                  <ArrowUp className="mx-auto" />
                </button>
              </div>
              <div className="col-start-1">
                <button
                  className={`w-full p-4 rounded-lg ${
                    activeKeys.has('ArrowLeft')
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                  onMouseDown={() => handleButtonPress('left')}
                  onMouseUp={() => handleButtonRelease('left')}
                  onMouseLeave={() => handleButtonRelease('left')}
                  onTouchStart={() => handleButtonPress('left')}
                  onTouchEnd={() => handleButtonRelease('left')}
                >
                  <ArrowLeft className="mx-auto" />
                </button>
              </div>
              <div className="col-start-3">
                <button
                  className={`w-full p-4 rounded-lg ${
                    activeKeys.has('ArrowRight')
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                  onMouseDown={() => handleButtonPress('right')}
                  onMouseUp={() => handleButtonRelease('right')}
                  onMouseLeave={() => handleButtonRelease('right')}
                  onTouchStart={() => handleButtonPress('right')}
                  onTouchEnd={() => handleButtonRelease('right')}
                >
                  <ArrowRight className="mx-auto" />
                </button>
              </div>
              <div className="col-start-2">
                <button
                  className={`w-full p-4 rounded-lg ${
                    activeKeys.has('ArrowDown')
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                  onMouseDown={() => handleButtonPress('backward')}
                  onMouseUp={() => handleButtonRelease('backward')}
                  onMouseLeave={() => handleButtonRelease('backward')}
                  onTouchStart={() => handleButtonPress('backward')}
                  onTouchEnd={() => handleButtonRelease('backward')}
                >
                  <ArrowDown className="mx-auto" />
                </button>
              </div>
            </div>
          </div>

          {/* Power Control */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Power className="text-blue-600" />
                <span className="font-medium">Power Control</span>
              </div>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={power}
                  onChange={(e) => handlePowerChange(parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="min-w-[4ch] text-right">{power}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Command History */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="text-blue-600" />
            <span className="font-medium">Command History</span>
          </div>
          <div className="space-y-2">
            {commandHistory.map((cmd, index) => (
              <div 
                key={index}
                className="flex items-center justify-between bg-gray-50 p-2 rounded"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium capitalize">{cmd.command}</span>
                  <span className="text-sm text-gray-500">Power: {cmd.power}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">{cmd.timestamp}</span>
                  <span className="text-sm text-blue-600">{cmd.latency}ms</span>
                </div>
              </div>
            ))}
            {commandHistory.length === 0 && (
              <div className="text-gray-500 text-center py-2">
                No commands sent yet
              </div>
            )}
          </div>
        </div>

        {/* Connection Status */}
        <div className="text-center">
          <span className={`inline-flex items-center gap-2 ${
            connected ? 'text-green-600' : 'text-red-600'
          }`}>
            <span className={`h-2 w-2 rounded-full ${
              connected ? 'bg-green-600' : 'bg-red-600'
            }`} />
            {connected ? 'Connected' : 'Reconnecting...'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default App;