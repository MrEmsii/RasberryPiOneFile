# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple test for NeoPixels on Raspberry Pi
import time
import board
import neopixel
import numpy as np
import random
import RPi.GPIO as GPIO

import ConfigControl
import Another

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(16, GPIO.OUT)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)

led_red_PWM = GPIO.PWM(12, 50)
led_green_PWM = GPIO.PWM(26, 50)
led_blue_PWM = GPIO.PWM(16, 50)

led_red_PWM.start(0)
led_green_PWM.start(0)
led_blue_PWM.start(0)

path = "/samba/python/"

# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D21

# The number of NeoPixels
num_pixels = 15

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB

try:
    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness = float(ConfigControl.collect_Config(path,"brightness")), auto_write=False, pixel_order=ORDER)
except:
    pass

@Another.save_error_to_file("error_log.txt")

def leds_print(rgb, br):
    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness = br, auto_write=False, pixel_order=ORDER)
    pixels.fill(rgb)
    pixels.show()
    led_string(rgb, br)

def wheel(pos):
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

def rainbow_cycle(wait):
    bra = float(ConfigControl.collect_Config(path,"brightness"))
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
   
        leds_print(pixels[i], bra)

        time.sleep(wait)

def constant():
        color_index = int(ConfigControl.collect_Config(path, "color"))
        color_list = [ (0, 0, 0),
                       (255, 0, 0),   (0, 255, 0),   (0, 0, 255), 
                       (204, 51, 0), (10 ,255, 30) , (255, 0, 255), 
                       (50, 50, 205), (50, 120, 50), (0, 255, 255), 
                       (255,255,255)
                    ]
        return color_list[color_index]

def stair(wait, color):
    for i in np.arange(0, 0.8, wait/2):
        leds_print(color, i)
        time.sleep(wait)    
    
    for i in np.arange(0.8, 0, -wait/2):
        leds_print(color, i)
        time.sleep(wait)    
    
def main():
    try:
        effects = int(ConfigControl.collect_Config(path, "effects"))
    except TypeError:
        print(effects)
        effects = 0
        print("Wtf")

    speed = float(ConfigControl.collect_Config(path, "leds_speed"))
    if effects == 1:
        leds_print(constant(), float(ConfigControl.collect_Config(path,"brightness")))
    elif effects == 2:
        stair(0.004*speed, constant())
    elif effects == 3:
        stair(0.004*speed, (random.randint(0,255), random.randint(0,255), random.randint(0,255)))    
    elif effects == 4:
        rainbow_cycle(0.01/speed)
    else:
        leds_print([0,0,0], 0)
        time.sleep(1)

def led_string(color, i):
    led_red_PWM.ChangeDutyCycle(int(color[0]/255*100*i))
    led_green_PWM.ChangeDutyCycle(int(color[1]/255*100*i))
    led_blue_PWM.ChangeDutyCycle(int(color[2]/255*100*i))

def led_string_stop():
    led_red_PWM.ChangeDutyCycle(0)
    led_green_PWM.ChangeDutyCycle(0)
    led_blue_PWM.ChangeDutyCycle(0)