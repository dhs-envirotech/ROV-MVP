import machine
import time
import network
import socket

from config import SSID, PASS

input1 = machine.Pin(0, machine.Pin.OUT)
input2 = machine.Pin(15, machine.Pin.OUT)

def motor_forward():
    print("Motor moving forward")
    input1.value(1)
    input2.value(0)

def motor_backward():
    print("Motor moving backward")
    input1.value(0)
    input2.value(1)

def motor_off():
    print("Motor off")
    input1.value(0)
    input2.value(0)

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
                time.sleep(1)
        print("Connected to WiFi. IP address:", self.sta_if.ifconfig()[0])

def web_page():
    html = """<!DOCTYPE html>
    <html>
    <head>
        <title>Motor Control</title>
    </head>
    <body>
        <h1>Motor Control</h1>
        <form action="/forward">
            <input type="submit" value="Forward">
        </form><br>
        <form action="/backward">
            <input type="submit" value="Backward">
        </form><br>
        <form action="/off">
            <input type="submit" value="Off">
        </form>
    </body>
    </html>"""
    return html

def main():
    wifi = WiFiConnection(SSID, PASS)
    wifi.connect()

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    print('Listening on', addr)

    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024)
        request = str(request)
        print('Request:', request)

        if '/forward' in request:
            motor_forward()
        elif '/backward' in request:
            motor_backward()
        elif '/off' in request:
            motor_off()

        response = web_page()
        cl.send('HTTP/1.1 200 OK\n')
        cl.send('Content-Type: text/html\n')
        cl.send('Connection: close\n\n')
        cl.sendall(response)
        cl.close()

if __name__ == "__main__":
    main()
