# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple test for NeoPixels on Raspberry Pi
import time
import board
import neopixel
import numpy as np

import ConfigControl
import Another

path = "/samba/python/"

# Choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D18
# NeoPixels must be connected to D10, D12, D18 or D21 to work.
pixel_pin = board.D21

# The number of NeoPixels
num_pixels = 15

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness = float(ConfigControl.collect_Config(path,"brightness")), auto_write=False, pixel_order=ORDER)

@Another.save_error_to_file("log_bledow.txt")
# def thred(wait):
#         t1 = threading.Thread(target=rainbow_cycle, args=(wait,))
#         t1.start()

def leds_print(rgb, br):
    pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness = br, auto_write=False, pixel_order=ORDER)
    pixels.fill(rgb)
    pixels.show()

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
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

        #print(pixels[i], float(ConfigControl.collect_Config(path,"brightness")))
        time.sleep(wait)

def constant():
        color_index = int(ConfigControl.collect_Config(path, "color"))
        color_list = [ (0, 0, 0),
                       (255, 0, 0),   (0, 255, 0),   (0, 0, 255), 
                       (255, 255, 0), (10 ,255, 30) , (255, 0, 255), 
                       (50, 50, 205), (50, 120, 50), (0, 255, 255), 
                       (255,255,255)
                    ]
        return color_list[color_index]

def stair(wait):
    color = constant()
    for i in np.arange(0, 0.5, wait/5):
        # pixel_index = (i * 256 // num_pixels) + j
        # pixels[i] = wheel(pixel_index & 255)
        leds_print(color, i)
        time.sleep(wait)    
    
    for i in np.arange(0.5, 0, -wait/5):
        # pixel_index = (i * 256 // num_pixels) + j
        # pixels[i] = wheel(pixel_index & 255)
        leds_print(color, i)
        time.sleep(wait)    
    
def main():
    effects = int(ConfigControl.collect_Config(path, "effects"))
    if effects == 1:
        leds_print(constant(), float(ConfigControl.collect_Config(path,"brightness")))
    elif effects == 2:
        stair(0.01)
    elif effects == 3:
        rainbow_cycle(0.01)


