import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import time
import asyncio
import cv2
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class VideoStream:
    def __init__(self):
        self.active = False
        self.cap = None
        self.frame_queue = asyncio.Queue(maxsize=1)
        self.last_frame_time = 0
        self.min_frame_interval = 1/60
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.encode_params = [cv2.IMWRITE_JPEG_QUALITY, 65]
        self.camera_lock = Lock()
        self.initialization_error = None
    
    def initialize_camera(self):
        try:
            with self.camera_lock:
                if self.cap is None:
                    self.cap = cv2.VideoCapture(0)
                    if not self.cap.isOpened():
                        raise RuntimeError("Failed to open camera")
                    
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                    self.cap.set(cv2.CAP_PROP_FPS, 60)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    print("[SERVER] Camera initialized successfully")
                    return True
        except Exception as e:
            self.initialization_error = str(e)
            print(f"[SERVER] Camera initialization error: {e}")
            return False
    
    async def start(self):
        success = await asyncio.get_event_loop().run_in_executor(
            self.executor, self.initialize_camera)
        
        if success:
            self.active = True
            asyncio.create_task(self.capture_frames())
            print("[SERVER] Video stream started")
            return True
        else:
            print(f"[SERVER] Failed to start video stream: {self.initialization_error}")
            return False
    
    def stop(self):
        self.active = False
        if self.cap is not None:
            with self.camera_lock:
                self.cap.release()
                self.cap = None
        print("[SERVER] Video stream stopped")
    
    def capture_and_encode_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return None
            
        with self.camera_lock:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (480, 360))
                _, buffer = cv2.imencode('.jpg', frame, self.encode_params)
                return base64.b64encode(buffer).decode('utf-8')
        return None
    
    async def capture_frames(self):
        while self.active:
            current_time = time.time()
            
            if current_time - self.last_frame_time >= self.min_frame_interval:
                frame_data = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.capture_and_encode_frame)
                
                if frame_data:
                    try:
                        while not self.frame_queue.empty():
                            await self.frame_queue.get()
                        
                        await self.frame_queue.put({
                            'frame': frame_data,
                            'timestamp': current_time
                        })
                        self.last_frame_time = current_time
                    except:
                        pass
            
            await asyncio.sleep(0.001)

class AsyncRobotWebSocket(tornado.websocket.WebSocketHandler):
    clients = set()
    video_stream = VideoStream()
    last_frame_time = time.time()
    frame_count = 0
    video_tasks = {}  # Store video streaming tasks per client
    
    def check_origin(self, origin):
        return True
    
    def open(self):
        print("\n[SERVER] Client connected")
        AsyncRobotWebSocket.clients.add(self)
        self.video_active = False  # Track video state per client
        self.write_message(json.dumps({
            'type': 'connection_status',
            'data': {'status': 'connected'}
        }))
        print("[SERVER] Ready to receive commands")
    
    async def handle_movement(self, command, power):
        """Handle movement commands separately from video"""
        print(f"\n[SERVER] ⮕ Received movement command: {command} (Power: {power}%)")
        response = {
            'type': 'command_response',
            'data': {
                'status': 'processed',
                'command': command,
                'power': power,
                'timestamp': time.time()
            }
        }
        await self.write_message(json.dumps(response))
        print(f"[SERVER] ✓ Processed command: {command} (Power: {power}%)")

    async def handle_video(self):
        """Handle video streaming separately"""
        self.video_active = True
        print("\n[SERVER] Starting video stream for client...")
        success = await AsyncRobotWebSocket.video_stream.start()
        
        if success:
            while self.video_active and AsyncRobotWebSocket.video_stream.active:
                try:
                    frame_data = await AsyncRobotWebSocket.video_stream.frame_queue.get()
                    
                    # Calculate FPS
                    current_time = time.time()
                    AsyncRobotWebSocket.frame_count += 1
                    elapsed = current_time - AsyncRobotWebSocket.last_frame_time
                    
                    if elapsed >= 1.0:
                        fps = AsyncRobotWebSocket.frame_count / elapsed
                        AsyncRobotWebSocket.frame_count = 0
                        AsyncRobotWebSocket.last_frame_time = current_time
                        frame_data['fps'] = round(fps, 1)
                    
                    if self.ws_connection is None:
                        break
                        
                    await self.write_message(json.dumps({
                        'type': 'video_frame',
                        'data': frame_data
                    }))
                except Exception as e:
                    print(f"[SERVER] Video streaming error: {e}")
                    break
    
    async def on_message(self, message):
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'movement_command':
                # Handle movement commands immediately
                command = data['data']['command']
                power = data['data'].get('power', 100)
                await self.handle_movement(command, power)
            
            elif message_type == 'power_update':
                power = data['data'].get('power', 100)
                print(f"\n[SERVER] ⚡ Power level updated: {power}%")
            
            elif message_type == 'start_video':
                if not self.video_active:
                    # Start video in a separate task
                    task = asyncio.create_task(self.handle_video())
                    self.video_tasks[id(self)] = task
            
            elif message_type == 'stop_video':
                self.video_active = False
                if id(self) in self.video_tasks:
                    self.video_tasks[id(self)].cancel()
                    del self.video_tasks[id(self)]
                print("\n[SERVER] Stopping video stream for client...")
                
        except Exception as e:
            print(f"[SERVER] Message handling error: {e}")
    
    def on_close(self):
        print("\n[SERVER] Client disconnected")
        self.video_active = False
        if id(self) in self.video_tasks:
            self.video_tasks[id(self)].cancel()
            del self.video_tasks[id(self)]
        AsyncRobotWebSocket.clients.remove(self)
        if len(AsyncRobotWebSocket.clients) == 0:
            AsyncRobotWebSocket.video_stream.stop()

def main():
    app = tornado.web.Application([
        (r"/ws", AsyncRobotWebSocket),
    ])
    
    print("\n[SERVER] Starting server on http://127.0.0.1:5000")
    print("[SERVER] Waiting for client connection...")
    app.listen(5000)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    except Exception as e:
        print(f"\n[SERVER] Error: {e}")