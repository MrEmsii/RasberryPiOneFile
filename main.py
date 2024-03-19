# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import os
import datetime 
import threading
import time
from subprocess import check_output
from gpiozero import CPUTemperature
import psutil
import setproctitle
import inspect

import DataBaseControl
import Temperature_Calculation
import API_LCD_I2C
import WeatherControl
import ConfigControl
import Another
import LEDs_Controler
import IR_Controler

MyLCD = API_LCD_I2C.lcd()
path = os.path.join("/samba/python/")


class thread:
    def Table_Maker_thread(path, file, columns, table_name):
        t_tm = threading.Thread(target=operation.Table_Maker, args=(path, file, columns, table_name,))
        t_tm.name = inspect.stack()[0][3]
        t_tm.start()
        t_tm.join()

    def Temp_Saver_thread():
        t_ts = threading.Thread(target=operation.Temp_Calc)
        t_ts.name = inspect.stack()[0][3]
        t_ts.start()
        t_ts.join()

    def localization_thread():
        t_local = threading.Thread(target=operation.localization)
        t_local.name = inspect.stack()[0][3]
        t_local.start()
        t_local.join()

    def WeatherCalc_thread():
        t_ws = threading.Thread(target=operation.Weather_Calc)
        t_ws.name = inspect.stack()[0][3]
        t_ws.start()

    def GetIP_thread():
        t_gIP = threading.Thread(target=operation.get_ip)
        t_gIP.name = inspect.stack()[0][3]
        t_gIP.start()
    
    def thread_Control_thread():
        t_tC = threading.Thread(target=control.thread_Control)
        t_tC.name = inspect.stack()[0][3]
        t_tC.start()

    def LCD_Control_thread(time_stop_LCD, time_one_segment):
        t_LCD = threading.Thread(target=control.LCD_Control, args=(time_stop_LCD, time_one_segment,))
        t_LCD.name = thread.LCD_Control_thread.__name__
        t_LCD.start()

    def LEDs_thread():
        t_LED = threading.Thread(target=control.LEDs)
        t_LED.name = inspect.stack()[0][3]
        t_LED.start()

    def IRDa_Control():
        t_IRDa = threading.Thread(target=control.IRDa_Control)
        t_IRDa.name = inspect.stack()[0][3]
        t_IRDa.start()

class operation:
    def Table_Maker(file, columns, table_name):
        DataBaseControl.table_maker(DataBaseControl.connectBase(file), columns, table_name)
        control.name_thread_start((threading.current_thread().getName()))

    def Temp_Calc():
        Temperature_Calculation.save(path)
        control.name_thread_start((threading.current_thread().getName()))

    def localization():
        data = operation.Weather_City()
        ConfigControl.edit_Config(path,[("city", data[0]),("IP_query", data[1])])
        control.name_thread_start((threading.current_thread().getName()))

    def Weather_Calc():
        api_key = ConfigControl.collect_Config(path, name="api_key")
        base_url = ConfigControl.collect_Config(path, name="base_url")
        localization = ConfigControl.collect_Config(path, name="city")
        list_Weather = WeatherControl.weather(localization, api_key, base_url)
        time_update = str(datetime.datetime.now())
        list_Weather.append(("time_update",time_update))
        ConfigControl.edit_Config(path, list_Weather)
        control.name_thread_start((threading.current_thread().getName()))

    def Weather_City():
        localization_url = ConfigControl.collect_Config(path,"localization_url")
        return WeatherControl.localization(str(localization_url))

    def get_ip():
        cmd = str(check_output("hostname -I | cut -d\' \' -f1", shell=True).decode("utf-8").strip())
        if len(cmd) > 5 and len(cmd) < 16:
            cmd
        else:
            cmd = "No IP"
        ConfigControl.edit_Config(path,[("IP_home",cmd)])
        control.name_thread_start((threading.current_thread().getName()))

class control:
    @Another.save_error_to_file("log_bledow.txt")

    def name_thread_start(name):
        return print(str(datetime.datetime.now()), 5*" ", str(name), (30-len(name))*" ", "started !")

    def LEDs():
        control.name_thread_start((threading.current_thread().getName()))
        while True:
            LEDs_Controler.main()
            time.sleep(1)

    def IRDa_Control():
        IR_Controler.main()
        control.name_thread_start((threading.current_thread().getName()))

    def LCD_Control(time_stop_LCD, wait):
        control.name_thread_start((threading.current_thread().getName()))
        while datetime.datetime.now() < time_stop_LCD:
            MyLCD.lcd_display_string_pos("Data: " + str(datetime.date.today()), 3, 2)
            for i in range(int(wait/0.2)):
                clock = datetime.datetime.now()
                MyLCD.lcd_display_string_pos("Time: " + clock.strftime("%H:%M:%S"), 2, 2)
                time.sleep(0.2)
            MyLCD.lcd_clear()

            for i in range(int(wait/3)):
                city = ConfigControl.collect_Config(path,"city")
                temp_outside = ConfigControl.collect_Config(path,"temp_outside")
                current_p_h = ConfigControl.collect_Config(path,"current_humidity") + " " + ConfigControl.collect_Config(path,"current_pressure")
                info_weather = ConfigControl.collect_Config(path,"info_weather")
                MyLCD.lcd_display_string_pos(str(city), 1, int((20 - len(str(city)))/2))
                MyLCD.lcd_display_string_pos(str(info_weather), 2, int((20 - len(str(info_weather)))/2))
                MyLCD.lcd_display_string_pos(str(temp_outside), 3, int((20 - len(str(temp_outside)))/2))
                MyLCD.lcd_display_string_pos(str(current_p_h), 4, int((20 - len(str(current_p_h)))/2))
                time.sleep(3)
            temp_list = Temperature_Calculation.tempALL()    
            MyLCD.lcd_clear()

            MyLCD.lcd_display_string_pos("Temperature:", 1, 4)
            for i in range(int(wait)):
                temp_1 = " Room = " + str(temp_list[0]) + "\u00dfC "
                temp_2 = " OutDoor = " + str(temp_list[1]) + "\u00dfC "
                temp_3 = " RaspPI = " + str(CPUTemperature().temperature)[0:4] + "\u00dfC "
                
                MyLCD.lcd_display_string_pos(str(temp_1), 2, 4)
                MyLCD.lcd_display_string_pos(str(temp_2), 3, 1)
                MyLCD.lcd_display_string_pos(str(temp_3), 4, 2)
                time.sleep(0.7)
            MyLCD.lcd_clear()

            trash =  "CPU  " + "RAM " + "DISK "
            MyLCD.lcd_display_string_pos(trash, 1, 3)
            ip_home = ConfigControl.collect_Config(path,"IP_home")
            ip_query = ConfigControl.collect_Config(path,"IP_query")
            MyLCD.lcd_display_string_pos(ip_query, 3, int((20 - len(ip_query))/2) - 1)
            MyLCD.lcd_display_string_pos(ip_home, 4, int((20 - len(ip_home))/2) - 1)
            for i in range(int(wait*4)):
                mesh = str(str(psutil.cpu_percent(interval = 0.2)) + "% " + str(psutil.virtual_memory().percent) + "% " + str(psutil.disk_usage('/').percent) + "%")
                MyLCD.lcd_display_string_pos(mesh, 2, 2)
                time.sleep(.3)
            MyLCD.lcd_clear()

        MyLCD.backlight(0)

    @Another.save_error_to_file("log_bledow.txt")
    def thread_Control():
        control.name_thread_start((threading.current_thread().getName()))

        thread.IRDa_Control()
        thread.LEDs_thread()
        thread.localization_thread()

        start_time = time_start_WeatherCalc = time_start_get_ip = time_start_TempSaver = time_start_LCD = datetime.datetime.now()
        date = datetime.datetime(start_time.year, start_time.month, start_time.day)

        time_start_LCD = date + datetime.timedelta(hours=7)
        time_stop_LEDs = date + datetime.timedelta(hours=23)

        while True:
            if datetime.datetime.now() >= time_start_LCD:
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(hours=7)
                time_stop_LCD = time_start_LCD + datetime.timedelta(hours=15)
                
                thread.LCD_Control_thread(time_stop_LCD, time_one_segment = 3)
                time_start_LCD = datetime.datetime(time_start_LCD.year, time_start_LCD.month, time_start_LCD.day) + datetime.timedelta(days=1, hours=7)

            if datetime.datetime.now() >= time_start_WeatherCalc:
                thread.WeatherCalc_thread()
                time_start_WeatherCalc += datetime.timedelta(minutes=10)

            if datetime.datetime.now() >= time_start_get_ip:
                thread.GetIP_thread()
                time_start_get_ip += datetime.timedelta(minutes=5)
                
            if datetime.datetime.now() >= time_start_TempSaver:
                thread.Temp_Saver_thread()
                time_start_TempSaver += datetime.timedelta(minutes=3)
                
            if datetime.datetime.now() >= time_stop_LEDs:
                time_stop_LEDs = time_stop_LEDs + datetime.timedelta(days=1)
                data = [("color", 0), ("effects", 1)]
                ConfigControl.edit_Config(path, data)  

            time.sleep(5)

def startingProces():
    MyLCD.backlight(0)
    if os.path.isfile(path + "Heat.db") == False:
        columns = ("data", "godzina", "temp_dot", "temp_comma", "jednostka")
        thread.Table_Maker_thread(path, "Heat.db", columns, "temperatura") 

    if os.path.isfile(path + "config.json") == False:
        dictionary = {
            "api_key": input("ENTER api_key \n"),
            "base_url": input("ENTER base_url \n"),
            "localization_url": input("ENTER localization_url \n"),
            "city": "",
            "temp_outside": "",
            "current_pressure": "",
            "current_humidity": "",
            "info_weather": "",
            "IP": "",
            "IP_query": "",
            "color": "",
            "brightness": "0.5",
            "effect": "1",
            "time_update": str(datetime.datetime.now())
        } 
        ConfigControl.insert_Config(path, data=dictionary)
        
    data = [("color", 0), ("effects", 1)]
    ConfigControl.edit_Config(path, data)  


if __name__ == '__main__':
    startingProces()
    thread.thread_Control_thread()  # !!!!
    setproctitle.setproctitle("Emsii-LCD")