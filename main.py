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

class thread:
    def Table_Maker_thread(path, file, columns, table_name):
        t1 = threading.Thread(target=operation.Table_Maker, args=(path, file, columns, table_name,))
        t1.start()
        t1.join()

    def Temp_Saver_thread():
        t2 = threading.Thread(target=operation.Temp_Calc)
        t2.start()

    def localization_thread():
        t3_0 = threading.Thread(target=operation.localization)
        t3_0.start()
        t3_0.join()

    def WeatherCalc_thread():
        t3_1 = threading.Thread(target=operation.Weather_Calc)
        t3_1.start()

    def GetIP_thread():
        t4 = threading.Thread(target=operation.get_ip)
        t4.start()
    
    def thread_Control_thread():
        t5 = threading.Thread(target=Control.thread_Control)
        t5.start()

    def LCD_Control_thread(time_stop_LCD, time_one_segment):
        t5 = threading.Thread(target=Control.LCD_Control, args=(time_stop_LCD, time_one_segment,))
        t5.start()
    
class operation:
    def Table_Maker(file, columns, table_name):
        back = DataBaseControl.table_maker(DataBaseControl.connectBase(file), columns, table_name)
        print(back)

    def Temp_Calc():
        Temperature_Calculation.save(path)

    def localization():
        ConfigControl.edit_Config(path,[("localization", operation.Weather_City())])

    def Weather_Calc():
        api_key = ConfigControl.collect_Config(path, name="api_key")
        base_url = ConfigControl.collect_Config(path, name="base_url")
        localization = ConfigControl.collect_Config(path, name="localization")
        list_Weather = WeatherControl.weather(localization, api_key, base_url)
        time_update = str(datetime.datetime.now())
        list_Weather.append(("time_update",time_update))
        ConfigControl.edit_Config(path, list_Weather)

    def Weather_City():
        localization_url = ConfigControl.collect_Config(path,"localization_url")
        return WeatherControl.localization(str(localization_url))

    def get_ip():
        cmd = str(check_output("hostname -I | cut -d\' \' -f1", shell=True).decode("utf-8").strip())
        if len(cmd) > 5 and len(cmd) < 16:
            cmd
        else:
            cmd = "No IP"
        ConfigControl.edit_Config(path,[("IP",cmd)])


class Control:
    def LCD_Control(time_stop_LCD, wait):
        while datetime.datetime.now() < time_stop_LCD:
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
                time.sleep(1)
            MyLCD.lcd_clear()

            for i in range(int(wait/3)):
                city = ConfigControl.collect_Config(path,"localization")
                temp_outside = ConfigControl.collect_Config(path,"temp_outside")
                current_p_h = ConfigControl.collect_Config(path,"current_humidity") + " " + ConfigControl.collect_Config(path,"current_pressure")
                info_weather = ConfigControl.collect_Config(path,"info_weather")
                MyLCD.lcd_display_string_pos(str(city), 1, int((20 - len(str(city)))/2))
                MyLCD.lcd_display_string_pos(str(temp_outside), 3, int((20 - len(str(temp_outside)))/2))
                MyLCD.lcd_display_string_pos(str(current_p_h), 4, int((20 - len(str(current_p_h)))/2))
                MyLCD.lcd_display_string_pos(str(info_weather), 2, int((20 - len(str(info_weather)))/2))
                time.sleep(3)
                # if len(info_weather) >= 18:
                #     for i in range (0, len(info_weather)):
                #         lcd_text = str((" "*16)) + info_weather + str((" "*16))[i:(i+20)]
                #         MyLCD.lcd_display_string(lcd_text,2)
                #         time.sleep(0.3)
                #         MyLCD.lcd_display_string(str((" "*16))[(22+i):i], 2)
                # else:
                #     MyLCD.lcd_display_string_pos(str(info_weather), 2, int((20 - len(str(info_weather)))/2))		
            MyLCD.lcd_clear()

            ip = ConfigControl.collect_Config(path,"IP")
            MyLCD.lcd_display_string_pos(ip, 1, int((20 - len(ip))/2) - 1)
            for i in range(int(wait*3)):
                cpu_per = "CPU= " + str(psutil.cpu_percent(interval = 0.5)) + "%"
                RAM_per = "RAM= " + str(psutil.virtual_memory().percent) + "%"
                disk_per = "DISK= " + str(psutil.disk_usage('/').percent) + "%"
                
                MyLCD.lcd_display_string_pos(cpu_per, 2, 4)
                MyLCD.lcd_display_string_pos(disk_per, 3, 3)
                MyLCD.lcd_display_string_pos(RAM_per, 4, 4)
                time.sleep(0.3)
            MyLCD.lcd_clear()
        MyLCD.backlight(0)
                    
    def thread_Control():
        time_start_WeatherCalc = datetime.datetime.now()
        time_start_get_ip = datetime.datetime.now()
        time_start_TempSaver = datetime.datetime.now()

        time_start_LCD = datetime.datetime.now()
        time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(hours=7)

        while True:
            if datetime.datetime.now() >= time_start_LCD:
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(hours=7)
                time_stop_LCD = time_start_LCD + datetime.timedelta(hours=15)
                
                thread.LCD_Control_thread(time_stop_LCD, time_one_segment = 3)
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(days=1, hours=7)
                print("LCD")

            if datetime.datetime.now() >= time_start_WeatherCalc:
                thread.WeatherCalc_thread()
                time_start_WeatherCalc += datetime.timedelta(minutes=10)
                print("Weather")    

            if datetime.datetime.now() >= time_start_get_ip:
                thread.GetIP_thread()
                time_start_get_ip += datetime.timedelta(minutes=5)
                print("IP")

            if datetime.datetime.now() >= time_start_TempSaver:
                thread.Temp_Saver_thread()
                time_start_TempSaver += datetime.timedelta(minutes=3)
                print("Temp")        

            time.sleep(1)

if __name__ == '__main__':
    try:
        path = os.path.join("/samba/", "python/")
        
        MyLCD.backlight(0)
        if os.path.isfile(path + "Heat.db") == False:
            columns = ("data", "godzina", "temp_dot", "temp_comma", "jednostka")
            thread.Table_Maker_thread(path, "Heat.db", columns, "temperatura") 

        if os.path.isfile(path + "config.json") == False:
            dictionary = {
                "api_key": input("ENTER api_key \n"),
                "base_url": input("ENTER base_url \n"),
                "localization_url": input("ENTER localization_url \n"),
                "localization": "1",
                "time_update": str(datetime.datetime.now())
            } 
            ConfigControl.insert_Config(path, data=dictionary)
        thread.localization_thread()
        thread.thread_Control_thread()  # !!!!

    except:
        traceback.print_exc()  
        Another.error_insert(traceback.format_exc())