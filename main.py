# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import os
import datetime 
import traceback
import threading
import time
from subprocess import check_output
from gpiozero import CPUTemperature
import psutil

import DataBaseControl
import Temperature_Calculation
import API_LCD_I2C
import WeatherControl
import ConfigControl
import Another

MyLCD = API_LCD_I2C.lcd()

now = datetime.datetime.now()

class thread:
    def Table_Maker_thread(path, file, columns, table_name):
        t1 = threading.Thread(target=operation.Table_Maker, args=(path, file, columns, table_name,))
        t1.start()
        t1.join()

    def Temp_Saver_thread(path):
        t2 = threading.Thread(target=operation.Temp_Calc, args=(path,))
        t2.start()

    def WeatherCalc_thread(localization, path):
        t3 = threading.Thread(target=operation.Weather_Calc, args=(localization, path,))
        t3.start()

    def GetIP_thread():
        t4 = threading.Thread(target=operation.get_ip)
        t4.start()
    
    def thread_Control_thread(path):
        t5 = threading.Thread(target=Control.thread_Control, args=(path,))
        t5.start()

    def LCD_Control_thread(time_now, time_stop_LCD, wait):
        t5 = threading.Thread(target=Control.LCD_Control, args=(time_now, time_stop_LCD, wait,))
        t5.start()
    
class operation:
    def Table_Maker(path, file, columns, table_name):
        back = DataBaseControl.table_maker(DataBaseControl.connectBase(path, file), columns, table_name)
        print(back)

    def Temp_Calc(path):
        Temperature_Calculation.save(path)
        
    def Weather_Calc(localization, path):
        api_key = ConfigControl.collect_Config(path, file="config.json", name="api_key")
        base_url = ConfigControl.collect_Config(path, file="config.json", name="base_url")
        list_Weather = WeatherControl.weather(localization, api_key, base_url)
        time_update = str(datetime.datetime.now())
        list_Weather.append(("time_update",time_update))
        ConfigControl.edit_Config(path, "config.json", list_Weather)

    def Weather_City(path, file):
        localization_url = ConfigControl.collect_Config(path,file,"localization_url")
        return WeatherControl.localization(str(localization_url))

    def get_ip():
        cmd = str(check_output("hostname -I | cut -d\' \' -f1", shell=True).decode("utf-8").strip())
        if len(cmd) > 5 and len(cmd) < 16:
            cmd
        else:
            cmd = "No IP"
        ConfigControl.edit_Config(path,"config.json",[("IP",cmd)])




class Control:
    def LCD_Control(time_start, time_stop, wait):
        while time_start < time_stop:
            MyLCD.lcd_display_string_pos("Data: " + str(datetime.date.today()), 3, 2)
            for i in range(int(wait/0.2)):
                clock = datetime.datetime.now()
                MyLCD.lcd_display_string_pos("Time: " + clock.strftime("%H:%M:%S"), 2, 2)
                time.sleep(0.2)
            MyLCD.lcd_clear()

            MyLCD.lcd_display_string_pos("Temperature:", 1, 4)
            for i in range(int(wait)):
                temp_1 = " Room = " + Temperature_Calculation.termW1() + "\u00dfC "
                temp_2 = " RaspPI = " + str(CPUTemperature().temperature)[0:4] + "\u00dfC "
                
                MyLCD.lcd_display_string_pos(str(temp_1), 2, 3)
                MyLCD.lcd_display_string_pos(str(temp_2), 3, 1)
                time.sleep(2)
            MyLCD.lcd_clear()
            
            for i in range(int(wait)):
                cpu_per = "CPU= " + str(psutil.cpu_percent(interval = 0.5)) + "%"
                RAM_per = "RAM= " + str(psutil.virtual_memory().percent) + "%"
                disk_per = "DISK= " + str(psutil.disk_usage('/').percent) + "%"
                ip = ConfigControl.collect_Config(path,"config.json","IP")

                MyLCD.lcd_display_string_pos(ip, 1, int((20 - len(ip))/2) - 1)
                MyLCD.lcd_display_string_pos(cpu_per, 2, 4)
                MyLCD.lcd_display_string_pos(disk_per, 3, 3)
                MyLCD.lcd_display_string_pos(RAM_per, 4, 4)
                time.sleep(1)
            MyLCD.lcd_clear()


        MyLCD.backlight(0)
        
            
    def thread_Control(path):

        localization = operation.Weather_City(path, "config.json")

        time_start_WeatherCalc = datetime.datetime.now()
        time_start_get_ip = datetime.datetime.now()
        time_start_TempSaver = datetime.datetime.now()

        time_start_LCD = datetime.datetime.now()

        while True:

            if datetime.datetime.now() >= time_start_LCD:
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(hours=7)
                time_stop_LCD = time_start_LCD + datetime.timedelta(hours=15)
                time_now = datetime.datetime.now()
                
                thread.LCD_Control_thread(time_now, time_stop_LCD, wait = 3)
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(days=1)
                print("LCD")

            if datetime.datetime.now() >= time_start_WeatherCalc:
                thread.WeatherCalc_thread(localization, path)
                time_start_WeatherCalc += datetime.timedelta(minutes=10)
                print("Weather")    

            if datetime.datetime.now() >= time_start_get_ip:
                thread.GetIP_thread()
                time_start_get_ip += datetime.timedelta(minutes=5)
                print("IP")

            if datetime.datetime.now() >= time_start_TempSaver:
                thread.Temp_Saver_thread(path)
                time_start_TempSaver += datetime.timedelta(minutes=3)
                print("Temp")        

            time.sleep(10)

if __name__ == '__main__':
    path = "/samba/python/"
    try:
        if os.path.isfile(path + "Heat.db") == False:
            columns = ("data", "godzina", "temp_dot", "temp_comma", "jednostka")
            thread.Table_Maker_thread(path, "Heat.db", columns, "temperatura")  
        if os.path.isfile(path + "config.json") == False:
            dictionary = {
                "api_key": input("ENTER api_key \n"),
                "base_url": input("ENTER base_url \n"),
                "localization_url": input("ENTER localization_url \n"),
                "time_update": str(datetime.datetime.now())
            } 
            ConfigControl.insert_Config(path,file="config.json", data=dictionary)

        thread.thread_Control_thread(path)  # !!!!

    except:
        traceback.print_exc()  
        Another.error_insert(traceback.format_exc())