import machine
import network
import socket
import time
import json

from config import SSID, PASS

class MotorController:
    def __init__(self, pin1, pin2):
        self.input1 = machine.Pin(pin1, machine.Pin.OUT)
        self.input2 = machine.Pin(pin2, machine.Pin.OUT)
        self.current_state = "off"

    def motor_forward(self):
        print("Motor moving forward")
        self.input1.value(1)
        self.input2.value(0)
        self.current_state = "forward"

    def motor_backward(self):
        print("Motor moving backward")
        self.input1.value(0)
        self.input2.value(1)
        self.current_state = "backward"

    def motor_off(self):
        print("Motor off")
        self.input1.value(0)
        self.input2.value(0)
        self.current_state = "off"

    def get_state(self):
        return self.current_state

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

def handle_request(request, motor_controller):
    if 'GET / ' in request:
        return serve_file('/index.html', 'text/html')
    elif 'GET /forward' in request:
        motor_controller.motor_forward()
        return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
            json.dumps({"state": motor_controller.get_state()})
        )
    elif 'GET /backward' in request:
        motor_controller.motor_backward()
        return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
            json.dumps({"state": motor_controller.get_state()})
        )
    elif 'GET /off' in request:
        motor_controller.motor_off()
        return 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{}'.format(
            json.dumps({"state": motor_controller.get_state()})
        )
    else:
        print("404 - Page not found")
        return 'HTTP/1.1 404 NOT FOUND\n\nPage not found'

def main():
    print("Starting program...")
    wifi = WiFiConnection(SSID, PASS)
    wifi.connect()

    motor_controller = MotorController(pin1=0, pin2=15)

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

        response = handle_request(request, motor_controller)
        cl.send(response)
        cl.close()
        print("Client connection closed")

if __name__ == "__main__":
    main()
