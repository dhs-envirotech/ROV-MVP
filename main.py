import machine
import network
import socket
import time
import json

from config import SSID, PASS

class MotorController:
    def __init__(self, name, pin1, pin2, pwm_pin):
        self.name = name
        self.input1 = machine.Pin(pin1, machine.Pin.OUT)
        self.input2 = machine.Pin(pin2, machine.Pin.OUT)
        self.pwm = machine.PWM(machine.Pin(pwm_pin), freq=1000)
        self.current_state = "off"
        self.pwm_value = 0
    
    def motor_forward(self):
        print(f"{self.name} moving forward")
        self.input1.value(1)
        self.input2.value(0)
        self.current_state = "forward"

    def motor_backward(self):
        print(f"{self.name} moving backward")
        self.input1.value(0)
        self.input2.value(1)
        self.current_state = "backward"

    def motor_off(self):
        print(f"{self.name} off")
        self.input1.value(0)
        self.input2.value(0)
        self.current_state = "off"

    def set_pwm(self, value):
        self.pwm_value = max(0, min(255, value))
        self.pwm.duty(self.pwm_value)
        print(f"{self.name} PWM set to {self.pwm_value}")

    def get_state(self):
        return {"name": self.name, "state": self.current_state, "pwm": self.pwm_value}

class WiFiConnection:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.sta_if = network.WLAN(network.STA_IF)

    def connect(self):
        if not self.sta_if.isconnected():
            print("Connecting to network...")
            self.sta_if.active(True)
            self.sta_if.connect(self.ssid, self.password)
            while not self.sta_if.isconnected():
                print("Waiting for connection...")
                time.sleep(1)
        print("Connected to WiFi. IP address:", self.sta_if.ifconfig()[0])

def serve_file(filename, content_type):
    print(f"Serving file: {filename}")
    with open(filename, 'r') as file:
        return 'HTTP/1.1 200 OK\nContent-Type: {}\n\n{}'.format(content_type, file.read())

def handle_request(request, motors):
    if 'GET / ' in request:
        return serve_file('/index.html', 'text/html')
    elif 'GET /state' in request:
        states = {motor_name: motor.get_state() for motor_name, motor in motors.items()}
        return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(json.dumps(states))
    
    for motor_name, motor in motors.items():
        if f'GET /{motor_name}/forward' in request:
            motor.motor_forward()
            return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
                json.dumps({"state": motor.get_state()})
            )
        elif f'GET /{motor_name}/backward' in request:
            motor.motor_backward()
            return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
                json.dumps({"state": motor.get_state()})
            )
        elif f'GET /{motor_name}/off' in request:
            motor.motor_off()
            return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
                json.dumps({"state": motor.get_state()})
            )
        elif f'GET /{motor_name}/pwm' in request and 'value=' in request:
            pwm_value = int(request.split('value=')[-1])
            motor.set_pwm(pwm_value)
            return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
                json.dumps({"state": motor.get_state()})
            )

    print("404 - Page not found")
    return 'HTTP/1.1 404 NOT FOUND\n\nPage not found'

def main():
    print("Starting program...")
    wifi = WiFiConnection(SSID, PASS)
    wifi.connect()

    motors = {
        "motor1": MotorController("Motor 1", pin1=0, pin2=15, pwm_pin=5),  # example PWM pin
        "motor2": MotorController("Motor 2", pin1=1, pin2=16, pwm_pin=5),  # example PWM pin
    }

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(5)
    print('Listening on', addr)

    while True:
        print("Waiting for a new client...")
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024).decode()
        print(f"Received request: {request}")

        response = handle_request(request, motors)
        cl.send(response)
        cl.close()
        print("Client connection closed")

if __name__ == "__main__":
    main()
