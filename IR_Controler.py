#-----------------------------------------#
# Name - IR-Finalized.py
# Description - The finalized code to read data from an IR sensor and then reference it with stored values
# Author - Lime Parallelogram
# License - Completely Free
# Date - 12/09/2019
#------------------------------------------------------------#
# Add more 26.10.2022 Emsii
#https://github.com/EmsiiDiss

import RPi.GPIO as GPIO
from datetime import datetime
import time
import Another, ConfigControl

pin = 20
# Static program vars
Buttons = [0x300FF30CF, 0x300FF18E7,  0x300FF7A85, 0x300FF10EF, 0x300FF38C7, 0x300FF5AA5, 0x300FF42BD, 0x300FF4AB5, 0x300FF52AD, 0x300FF6897, 0x300FF9867, 0x300FFB04F, 0x300FFE01F, 0x300FFA857, 0x300FF906F, 0x300FF22DD, 0x300FF02FD, 0x300FFC23D, 0x300FFA25D, 0x300FF629D, 0x300FFE21D] 
ButtonsNames = ["1",   		"2",     	 "3",      		 "4",    	  "5",		"6", 	 		"7", 		 "8", 		"9",	 	"0", 		"100+", 	"200+", 		"-", 		"+", 		"eq", 		"<<", 			">>",		 ">||",		 "ch-",			"ch",		"ch+"]  
#ButtonsIndex = [0				1			2			3			4			5				6				7		8			9			10				11				12			13		14			15				16			17				18			19			20		]
# Sets up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin, GPIO.IN)

path = "/samba/python/"

def getBinary():
	# Internal vars
	num1s = 0  # Number of consecutive 1s read
	binary = 1  # The binary value
	command = []  # The list to store pulse times in
	previousValue = 0  # The last value
	value = GPIO.input(pin)  # The current value

	# Waits for the sensor to pull pin low
	while value:
		time.sleep(0.01) # This sleep decreases CPU utilization immensely
		value = GPIO.input(pin)
		
	# Records start time
	startTime = datetime.now()
	
	while True:
		# If change detected in value
		if previousValue != value:
			now = datetime.now()
			pulseTime = now - startTime #Calculate the time of pulse
			startTime = now #Reset start time
			command.append((previousValue, pulseTime.microseconds)) #Store recorded data
			
		# Updates consecutive 1s variable
		if value:
			num1s += 1
		else:
			num1s = 0
		
		# Breaks program when the amount of 1s surpasses 10000
		if num1s > 10000:
			break
			
		# Re-reads pin
		previousValue = value
		value = GPIO.input(pin)
		
	# Converts times to binary
	for (typ, tme) in command:
		if typ == 1: #If looking at rest period
			if tme > 1000: #If pulse greater than 1000us
				binary = binary *10 +1 #Must be 1
			else:
				binary *= 10 #Must be 0
			
	if len(str(binary)) > 34: #Sometimes, there is some stray characters
		binary = int(str(binary)[:34])
		
	return binary
	
def convertHex(binaryValue):
	tmpB2 = int(str(binaryValue),2) #Temporarely propper base 2
	return hex(tmpB2)

@Another.save_error_to_file("error_log.txt")
def main():
	max_effects = 4
	while True:
		inData = convertHex(getBinary()) #Runs subs to get incoming hex value
		for button in range(len(Buttons)):#Runs through every value in list
			if hex(Buttons[button]) == inData: #Checks this against incoming
				indexButton = ButtonsNames.index(ButtonsNames[button])
				# print(ButtonsNames[button], indexButton) #Prints corresponding english name for button

				if int(indexButton) >= 0 and int(indexButton) <= 9:
					color = ButtonsNames[button]
					ConfigControl.edit_Config(path, [("color", int(color))])
					
				elif int(indexButton) == 14:
					ConfigControl.edit_Config(path, [("color", 10)])

				elif int(indexButton) == 15 or int(indexButton) == 16:
					effects = int(ConfigControl.collect_Config(path, "effects"))
					if int(indexButton) == 15:
						if effects <= max_effects and effects > 1:
							effects = effects - 1
					elif int(indexButton) == 16:
						if effects < max_effects and effects >= 1:
							effects = effects + 1	

					ConfigControl.edit_Config(path, [("effects", int(effects))])
						
				elif int(indexButton) >= 12 and int(indexButton) <= 13:
					brightness = float(ConfigControl.collect_Config(path, "brightness"))
					if int(indexButton) <= 12:
						brightness = brightness - 0.05
					else:
						brightness = brightness + 0.05
					if brightness > 0.8:
						brightness = 0.8
					elif brightness <= 0.01:
						brightness = 0.01		
					ConfigControl.edit_Config(path, [("brightness", float(brightness))])


