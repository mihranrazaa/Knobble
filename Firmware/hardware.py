# rtl_sdr_radio_scanner/hardware.py

import RPi.GPIO as GPIO
import time

class HardwareController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.encoder_clk = 22
        self.encoder_dt = 27
        self.encoder_sw = 17
        self.switch1 = 23
        self.switch2 = 24
        self.switch3 = 25

        self.last_clk = GPIO.input(self.encoder_clk)
        self.encoder_delta = 0
        self.last_press_time = 0

        for pin in [self.encoder_clk, self.encoder_dt, self.encoder_sw,
                    self.switch1, self.switch2, self.switch3]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def get_encoder_event(self):
        clk = GPIO.input(self.encoder_clk)
        dt = GPIO.input(self.encoder_dt)
        sw = GPIO.input(self.encoder_sw)
        event = None

        if clk != self.last_clk:
            if dt != clk:
                self.encoder_delta = 1
            else:
                self.encoder_delta = -1
            event = "ROTATE"

        self.last_clk = clk

        if not sw:
            press_duration = time.time() - self.last_press_time
            if self.last_press_time == 0:
                self.last_press_time = time.time()
            elif press_duration > 1:
                event = "LONG_PRESS"
                self.last_press_time = 0
            else:
                event = "PRESS"
                self.last_press_time = 0

        if event == "ROTATE" and not GPIO.input(self.encoder_sw):
            event = "PRESS_ROTATE"

        return event

    def switch1_pressed(self):
        return not GPIO.input(self.switch1)

    def switch2_pressed(self):
        return not GPIO.input(self.switch2)

    def switch3_pressed(self):
        return not GPIO.input(self.switch3)

