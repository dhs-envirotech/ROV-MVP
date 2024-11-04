from flask import Flask, request, jsonify
import RPi.GPIO as GPIO

app = Flask(__name__)

# Motor control class with GPIO setup
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

    def motor_forward(self):
        GPIO.output(self.input1, GPIO.HIGH)
        GPIO.output(self.input2, GPIO.LOW)
        self.current_state = "forward"
        print(f"{self.name} moving forward")

    def motor_backward(self):
        GPIO.output(self.input1, GPIO.LOW)
        GPIO.output(self.input2, GPIO.HIGH)
        self.current_state = "backward"
        print(f"{self.name} moving backward")

    def motor_off(self):
        GPIO.output(self.input1, GPIO.LOW)
        GPIO.output(self.input2, GPIO.LOW)
        self.current_state = "off"
        print(f"{self.name} off")

    def set_pwm(self, value):
        self.pwm_value = max(0, min(100, value))
        self.pwm.ChangeDutyCycle(self.pwm_value)
        print(f"{self.name} PWM set to {self.pwm_value}")

    def get_state(self):
        return {"name": self.name, "state": self.current_state, "pwm": self.pwm_value}

# Initialize motors dynamically
motors = {
    "motor1": MotorController("Motor 1", input1=17, input2=27, pwm_pin=4),
    "motor2": MotorController("Motor 2", input1=5, input2=6, pwm_pin=13)
}

# Flask routes
@app.route('/')
def home():
    return "Motor Controller is running"

@app.route('/state', methods=['GET'])
def get_states():
    states = {motor_name: motor.get_state() for motor_name, motor in motors.items()}
    return jsonify(states)

@app.route('/<motor_name>/forward', methods=['GET'])
def motor_forward(motor_name):
    if motor_name in motors:
        motors[motor_name].motor_forward()
        return jsonify(motors[motor_name].get_state())
    else:
        return "Motor not found", 404

@app.route('/<motor_name>/backward', methods=['GET'])
def motor_backward(motor_name):
    if motor_name in motors:
        motors[motor_name].motor_backward()
        return jsonify(motors[motor_name].get_state())
    else:
        return "Motor not found", 404

@app.route('/<motor_name>/off', methods=['GET'])
def motor_off(motor_name):
    if motor_name in motors:
        motors[motor_name].motor_off()
        return jsonify(motors[motor_name].get_state())
    else:
        return "Motor not found", 404

@app.route('/<motor_name>/pwm', methods=['GET'])
def set_pwm(motor_name):
    if motor_name in motors:
        pwm_value = request.args.get('value', default=0, type=int)
        motors[motor_name].set_pwm(pwm_value)
        return jsonify(motors[motor_name].get_state())
    else:
        return "Motor not found", 404

@app.route('/cleanup', methods=['GET'])
def gpio_cleanup():
    GPIO.cleanup()
    return "GPIO cleaned up"

# Run the Flask server
if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=80, debug=True)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("GPIO Clean up")
