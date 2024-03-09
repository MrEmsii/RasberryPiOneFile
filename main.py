# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import os
import traceback
import threading
import time
from subprocess import check_output

import datetime 
import DataBaseControl
import Temperature_Calculation
import API_LCD_I2C
import WeatherControl
import ConfigControl

MyLCD = API_LCD_I2C.lcd()

now = datetime.datetime.now()

class thread:
    def threadTableMaker(path, file, columns, table_name):
        t1 = threading.Thread(target=operation.Table_Maker, args=(path, file, columns, table_name,))
        t1.start()
        t1.join()

    def threadTempSaver(path):
        t2 = threading.Thread(target=operation.TempCalc, args=(path,))
        t2.start()

    def threadWeatherCalc(localization, path):
        t3 = threading.Thread(target=operation.WeatherCalc, args=(localization, path,))
        t3.start()

    def threadGetIP():
        t4 = threading.Thread(target=operation.get_ip)
        t4.start()
    
    def threadControl(path):
        t5 = threading.Thread(target=operation.threadControl, args=(path,))
        t5.start()

    def threadControlLCD(startLCD):
        t5 = threading.Thread(target=operation.ControlLCD, args=(startLCD,))
        t5.start()

class operation:
    def Table_Maker(path, file, columns, table_name):
        back = DataBaseControl.table_maker(DataBaseControl.connectBase(path, file), columns, table_name)
        print(back)

    def TempCalc(path):
        Temperature_Calculation.save(path)
        
    def WeatherCalc(localization, path):
        api_key = ConfigControl.collect(path, file="config.json", name="api_key")
        base_url = ConfigControl.collect(path, file="config.json", name="base_url")
        list_Weather = WeatherControl.weather(localization, api_key, base_url)
        time_update = str(datetime.datetime.now())
        list_Weather.append(("time_update",time_update))
        ConfigControl.editConf(path, "config.json", list_Weather)

    def WeatherCity(path, file):
        localization_url = ConfigControl.collect(path,file,"localization_url")
        return WeatherControl.localization(str(localization_url))

    def get_ip():
        cmd = str(check_output("hostname -I | cut -d\' \' -f1", shell=True).decode("utf-8").strip())
        if len(cmd) > 5 and len(cmd) < 16:
            return cmd
        else:
            return "No IP"

    def ControlLCD(time_start):
        time_now = datetime.datetime.now()
        time_stop = time_start + datetime.timedelta(hours=15)
        while time_now >= time_start and time_now < time_stop:
            data = str(datetime.date.today())
            MyLCD.lcd_display_string_pos(data + " " + time_now.strftime("%H:%M:%S"), 1, 1)
            MyLCD.lcd_display_string_pos(ConfigControl.collect("/samba/python/","config.json","temp_outside"), 2, 3)
            time.sleep(0.3)
            time_now = datetime.datetime.now()
            



    def threadControl(path):

        localization = operation.WeatherCity(path, "config.json")

        startWeatherCalc = datetime.datetime.now()
        start_get_ip = datetime.datetime.now()
        startTempSaver = datetime.datetime.now()

        startLCD = datetime.datetime.now()


        while True:

            if datetime.datetime.now() >= startLCD:
                startLCD = datetime.datetime(startLCD.year, startLCD.month, startLCD.day) + datetime.timedelta(hours=7)
                thread.threadControlLCD(startLCD)
                startLCD += datetime.timedelta(hours=15) 
                print("LCD")

            if datetime.datetime.now() >= startWeatherCalc:
                thread.threadWeatherCalc(localization, path)
                startWeatherCalc += datetime.timedelta(minutes=10)
                print("Weather")    

            if datetime.datetime.now() >= start_get_ip:
                thread.threadGetIP()
                start_get_ip += datetime.timedelta(minutes=1)
                print("IP")

            if datetime.datetime.now() >= startTempSaver:
                thread.threadTempSaver(path)
                startTempSaver += datetime.timedelta(minutes=3)
                print("Temp")        

            time.sleep(10)


if __name__ == '__main__':
    path = "/samba/python/"
    try:
        if os.path.isfile(path + "Heat.db") == False:
            columns = ("data", "godzina", "temp_dot", "temp_comma", "jednostka")
            thread.threadTableMaker(path, "Heat.db", columns, "temperatura")  
        if os.path.isfile(path + "config.json") == False:
            dictionary = {
                "api_key": input("ENTER api_key \n"),
                "base_url": input("ENTER base_url \n"),
                "localization_url": input("ENTER localization_url \n"),
                "time_update": str(datetime.datetime.now())
            } 
            ConfigControl.insertConf(path,file="config.json", data=dictionary)

        thread.threadControl(path)  # !!!!

    except:
        traceback.print_exc()  