import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import time
import asyncio
import cv2
import numpy as np
import base64
import RPi.GPIO as GPIO
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class MotorController:
    def __init__(self, name, input1, input2, pwm_pin):
        self.name = name
        self.input1 = input1
        self.input2 = input2
        self.pwm_pin = pwm_pin
        self.current_state = "off"
        self.pwm_value = 0

        # GPIO setup for the motor
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.input1, GPIO.OUT)
        GPIO.setup(self.input2, GPIO.OUT)
        GPIO.setup(self.pwm_pin, GPIO.OUT)

        # Set up PWM for the motor
        self.pwm = GPIO.PWM(self.pwm_pin, 100)
        self.pwm.start(0)

    def forward(self, power=100):
        GPIO.output(self.input1, GPIO.HIGH)
        GPIO.output(self.input2, GPIO.LOW)
        self.set_pwm(power)
        self.current_state = "forward"

    def backward(self, power=100):
        GPIO.output(self.input1, GPIO.LOW)
        GPIO.output(self.input2, GPIO.HIGH)
        self.set_pwm(power)
        self.current_state = "backward"

    def stop(self):
        GPIO.output(self.input1, GPIO.LOW)
        GPIO.output(self.input2, GPIO.LOW)
        self.set_pwm(0)
        self.current_state = "off"

    def set_pwm(self, value):
        self.pwm_value = max(0, min(100, value))
        self.pwm.ChangeDutyCycle(self.pwm_value)

    def get_state(self):
        return {"name": self.name, "state": self.current_state, "power": self.pwm_value}


class RobotController:
    def __init__(self):
        # Initialize motors
        self.left_motor = MotorController("Left Motor", input1=17, input2=27, pwm_pin=4)
        self.right_motor = MotorController(
            "Right Motor", input1=5, input2=6, pwm_pin=13
        )

    def move_forward(self, power=100):
        self.left_motor.forward(power)
        self.right_motor.forward(power)

    def move_backward(self, power=100):
        self.left_motor.backward(power)
        self.right_motor.backward(power)

    def turn_left(self, power=100):
        self.left_motor.backward(power)
        self.right_motor.forward(power)

    def turn_right(self, power=100):
        self.left_motor.forward(power)
        self.right_motor.backward(power)

    def stop(self):
        self.left_motor.stop()
        self.right_motor.stop()

    def get_state(self):
        return {
            "left_motor": self.left_motor.get_state(),
            "right_motor": self.right_motor.get_state(),
        }

    def cleanup(self):
        self.stop()
        GPIO.cleanup()


class VideoStream:
    def __init__(self):
        self.active = False
        self.cap = None
        self.frame_queue = asyncio.Queue(maxsize=1)
        self.last_frame_time = 0
        self.min_frame_interval = 1 / 60
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.encode_params = [cv2.IMWRITE_JPEG_QUALITY, 65]
        self.camera_lock = Lock()
        self.initialization_error = None

    # ... [Rest of VideoStream class implementation remains the same]


class AsyncRobotWebSocket(tornado.websocket.WebSocketHandler):
    clients = set()
    video_stream = VideoStream()
    robot_controller = RobotController()
    last_frame_time = time.time()
    frame_count = 0
    video_tasks = {}

    def check_origin(self, origin):
        return True

    def open(self):
        print("\n[SERVER] Client connected")
        AsyncRobotWebSocket.clients.add(self)
        self.video_active = False
        self.write_message(
            json.dumps({"type": "connection_status", "data": {"status": "connected"}})
        )
        print("[SERVER] Ready to receive commands")

    async def handle_movement(self, command, power):
        """Handle movement commands with actual motor control"""
        print(f"\n[SERVER] ⮕ Executing movement command: {command} (Power: {power}%)")

        # Execute the appropriate motor command
        if command == "forward":
            self.robot_controller.move_forward(power)
        elif command == "backward":
            self.robot_controller.move_backward(power)
        elif command == "left":
            self.robot_controller.turn_left(power)
        elif command == "right":
            self.robot_controller.turn_right(power)
        elif command == "stop":
            self.robot_controller.stop()

        # Get current state after movement
        state = self.robot_controller.get_state()

        response = {
            "type": "command_response",
            "data": {
                "status": "executed",
                "command": command,
                "power": power,
                "state": state,
                "timestamp": time.time(),
            },
        }
        await self.write_message(json.dumps(response))
        print(f"[SERVER] ✓ Executed command: {command} (Power: {power}%)")

    # ... [Rest of AsyncRobotWebSocket class implementation remains the same]

    def on_close(self):
        print("\n[SERVER] Client disconnected")
        self.video_active = False
        if id(self) in self.video_tasks:
            self.video_tasks[id(self)].cancel()
            del self.video_tasks[id(self)]
        AsyncRobotWebSocket.clients.remove(self)
        if len(AsyncRobotWebSocket.clients) == 0:
            AsyncRobotWebSocket.video_stream.stop()
            AsyncRobotWebSocket.robot_controller.stop()  # Stop motors when last client disconnects


def main():
    try:
        app = tornado.web.Application(
            [
                (r"/ws", AsyncRobotWebSocket),
            ]
        )

        print("\n[SERVER] Starting server on http://127.0.0.1:5000")
        print("[SERVER] Initializing GPIO and motors...")
        print("[SERVER] Waiting for client connection...")
        app.listen(5000)
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        AsyncRobotWebSocket.robot_controller.cleanup()
    except Exception as e:
        print(f"\n[SERVER] Error: {e}")
        AsyncRobotWebSocket.robot_controller.cleanup()


if __name__ == "__main__":
    main()
