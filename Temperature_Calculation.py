# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import w1thermsensor
import time

import DataBaseControl
import Another

sensors = w1thermsensor.W1ThermSensor()

@Another.save_error_to_file("error_log.txt")
def termW1():
    return str(float(sensors.get_temperature() - 3.5))[0:5]

def tempALL():
    temp_list = []
    for sensor in w1thermsensor.W1ThermSensor.get_available_sensors():
        temp_list.append(round(sensor.get_temperature() - 3.5, 1)) 
    return temp_list

def save():
    connect = DataBaseControl.connectBase("Heat.db")
    temp = termW1()
    data = [(str(time.strftime("%Y-%m-%d")), str(time.strftime("%H:%M:%S")), temp, temp.replace('.',','), str(chr(176) + "C")),]
    DataBaseControl.insert_Base(connect, "temperatura", data, place="NULL,")
    DataBaseControl.close_Base(connect, "yes")
    
