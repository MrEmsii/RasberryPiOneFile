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
import concurrent.futures

import DataBaseControl
import Temperature_Calculation
import API_LCD_I2C
import WeatherControl
import ConfigControl
import Another
import LEDs_Controler
import IR_Controler

MyLCD = API_LCD_I2C.lcd()
path = Another.full_path()

class thread:
    def Table_Maker_thread(file, columns, table_name):
        t_tm = threading.Thread(target=operation.Table_Maker, args=(file, columns, table_name,))
        t_tm.name = inspect.stack()[0][3]
        t_tm.start()
        t_tm.join()

    def Temp_Saver_thread():
        t_ts = threading.Thread(target=operation.Temp_Calc)
        t_ts.name = inspect.stack()[0][3]
        t_ts.start()
        t_ts.join()

    def Temp_Global():
        t_tg = threading.Thread(target=operation.Temp_Global)
        t_tg.name = inspect.stack()[0][3]
        t_tg.start()

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
    @Another.save_error_to_file("log_bledow.txt")
    def Table_Maker(file, columns, table_name):
        DataBaseControl.table_maker(DataBaseControl.connectBase(file), columns, table_name)
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def Temp_Calc():
        Temperature_Calculation.save()
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def Temp_Global():
        global temperature_list
        temperature_list = Temperature_Calculation.tempALL()
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def localization():
        data = operation.Weather_City()
        ConfigControl.edit_Config([("city", data[0]), ("IP_query", data[1])])
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def Weather_Calc():
        api_key = ConfigControl.collect_Config(name="api_key")
        base_url = ConfigControl.collect_Config(name="base_url")
        localization = ConfigControl.collect_Config(name="city")
        list_Weather = WeatherControl.weather(localization, api_key, base_url)
        time_update = str(datetime.datetime.now())
        list_Weather.append(("time_update",time_update))
        ConfigControl.edit_Config(list_Weather)
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def Weather_City():
        localization_url = ConfigControl.collect_Config("localization_url")
        return WeatherControl.localization(str(localization_url))

    @Another.save_error_to_file("log_bledow.txt")
    def get_ip():
        cmd = str(check_output("hostname -I | cut -d\' \' -f1", shell=True).decode("utf-8").strip())
        if len(cmd) > 5 and len(cmd) < 16:
            cmd
        else:
            cmd = "No IP"
        ConfigControl.edit_Config([("IP_home",cmd)])
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

class lcd_class:

    @Another.save_error_to_file("log_bledow.txt")
    def time(wait):
        MyLCD.lcd_display_string_pos("Data: " + str(datetime.date.today()), 3, 2)
        for i in range(int(wait/0.2)):
            clock = datetime.datetime.now()
            MyLCD.lcd_display_string_pos("Time: " + clock.strftime("%H:%M:%S"), 2, 2)
            time.sleep(0.2)

    @Another.save_error_to_file("log_bledow.txt")
    def weather():
        city = ConfigControl.collect_Config("city")
        temp_outside = ConfigControl.collect_Config("temp_outside")
        current_p_h = ConfigControl.collect_Config("current_humidity") + " " + ConfigControl.collect_Config("current_pressure")
        info_weather = ConfigControl.collect_Config("info_weather")
        MyLCD.lcd_display_string_pos(str(city), 1, int((20 - len(str(city)))/2))
        MyLCD.lcd_display_string_pos(str(temp_outside), 3, int((20 - len(str(temp_outside)))/2))
        MyLCD.lcd_display_string_pos(str(current_p_h), 4, int((20 - len(str(current_p_h)))/2))

        info_weather = " "*10 + info_weather + " "*10
        for i in range (0, len(info_weather) - 20):
            lcd_text = info_weather[i:(i+20)]
            MyLCD.lcd_display_string(lcd_text, 2)
            time.sleep(0.4)
       
    @Another.save_error_to_file("log_bledow.txt")
    def temperatura(wait):
        MyLCD.lcd_display_string_pos("Temperature:", 1, 4)
        Room_temp = " Room = " + str(temperature_list[0]) + "\u00dfC "
        OutDoor_temp = " OutDoor = " + str(temperature_list[1]) + "\u00dfC "
        MyLCD.lcd_display_string_pos(str(Room_temp), 2, 4)
        MyLCD.lcd_display_string_pos(str(OutDoor_temp), 3, 1)

        for i in range(int(wait)):
            RaspPI_temp = " RaspPI = " + str(CPUTemperature().temperature)[0:4] + "\u00dfC "
            MyLCD.lcd_display_string_pos(str(RaspPI_temp), 4, 2)
            time.sleep(0.7)

    @Another.save_error_to_file("log_bledow.txt")
    def pc_stats(wait):
        description =  "CPU   RAM   DISK"
        procent = f'0.0%   0.0%  0.0%'
        MyLCD.lcd_display_string_pos(description, 1, 3)
        MyLCD.lcd_display_string_pos(procent, 2, 2)
        
        ip_home = ConfigControl.collect_Config("IP_home")
        ip_query = ConfigControl.collect_Config("IP_query")
        
        MyLCD.lcd_display_string_pos(ip_query, 3, int((20 - len(ip_query))/2) - 1)
        MyLCD.lcd_display_string_pos(ip_home, 4, int((20 - len(ip_home))/2) - 1)

        MyLCD.lcd_display_string_pos(f'{psutil.virtual_memory().percent}%', 2, 8)
        MyLCD.lcd_display_string_pos(f'{psutil.disk_usage("/").percent}%', 2, 15)
        
        for i in range(int(wait*2)):
            MyLCD.lcd_display_string_pos(f'{psutil.cpu_percent(interval = 0.3)}%', 2, 2)
            time.sleep(.4)

class control:

    @Another.save_error_to_file("log_bledow.txt")
    def kill_process(name):
        for proc in psutil.process_iter():
            # check whether the process name matches
            if proc.name() == name:
                proc.kill()

    @Another.save_error_to_file("log_bledow.txt")
    def name_thread_start(name, pid):
        log = str(datetime.datetime.now()), 5*" ", str(name), (30-len(name))*" ", "started on pid: ", pid, "!"
        Another.save_logs_to_file(log)
        return print(log)

    @Another.save_error_to_file("log_bledow.txt")
    def LEDs():
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())
        while True:
            LEDs_Controler.main()
            time.sleep(0.4)

    @Another.save_error_to_file("log_bledow.txt")
    def IRDa_Control():
        IR_Controler.main()
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

    @Another.save_error_to_file("log_bledow.txt")
    def LCD_Control(time_stop_LCD, wait):
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())
        i = 0
        while datetime.datetime.now() < time_stop_LCD:
            if i % 2 == 0:
                thread.Temp_Global()
                lcd_class.time(wait)
            else:
                if i % 6 == 1:
                    lcd_class.temperatura(wait)
                elif i % 6 == 3:
                    lcd_class.weather()
                elif i % 6 == 5:
                    lcd_class.pc_stats(wait)

            i += 1
            MyLCD.lcd_clear()
        MyLCD.backlight(0)

    @Another.save_error_to_file("error_log.txt")
    def thread_Control():
        control.name_thread_start((threading.current_thread().getName()), threading.get_native_id())

        thread.IRDa_Control()
        thread.LEDs_thread()

        start_time = time_start_WeatherCalc = time_start_get_ip = time_start_TempSaver = time_start_LCD = time_start_get_localization = datetime.datetime.now()

        date = datetime.datetime(start_time.year, start_time.month, start_time.day)

        hour_start_LCD = ConfigControl.collect_Config("hour_start_LCD")
        hour_stop_LCD = ConfigControl.collect_Config("hour_stop_LCD")

        time_start_LCD = date + datetime.timedelta(hours=hour_start_LCD)
        time_stop_LCD = time_stop_LEDs = date + datetime.timedelta(hours=hour_stop_LCD)

        while True:
            now = datetime.datetime.now()
            current_time = int(now.strftime("%H"))

            date = datetime.datetime(start_time.year, start_time.month, start_time.day)

            if now >= time_start_get_localization:
                thread.localization_thread()
                time_start_get_localization += datetime.timedelta(minutes=60) 
                
            if now >= time_start_WeatherCalc and current_time < hour_stop_LCD and current_time >= hour_start_LCD: #process - off when LCD is off
                thread.WeatherCalc_thread()
                time_start_WeatherCalc += datetime.timedelta(minutes=5)

            if now >= time_start_get_ip:
                thread.GetIP_thread()
                time_start_get_ip += datetime.timedelta(minutes=5)
                
            if now >= time_start_TempSaver:
                thread.Temp_Saver_thread()
                time_start_TempSaver += datetime.timedelta(minutes=3)
                
            if now >= time_stop_LEDs:
                time_stop_LEDs = time_stop_LEDs + datetime.timedelta(days=1)
                data = [("color", 0), ("effects", 0)]
                brightness = ConfigControl.collect_Config("brightness")
                if brightness < 0.5:
                    brightness = 0.5
                    data.append(("brightness", 0.5))
                ConfigControl.edit_Config(data)  

            if now >= time_start_LCD:
                time_start_LCD = time_start_LCD + datetime.timedelta(days=1)
                thread.LCD_Control_thread(time_stop_LCD, time_one_segment=3)
                time_stop_LCD = time_stop_LCD + datetime.timedelta(days=1)
            
            if os.path.isfile(path + "error_log.txt") == True:
                print("Crash")
                MyLCD.lcd_clear()
                MyLCD.backlight(0)
                control.kill_process("Emsii_LCD")


            time.sleep(0.3)

@Another.save_error_to_file("error_log.txt")
def startingProces():
    MyLCD.backlight(0)
    # time.sleep(10)
    if os.path.isfile(path + "error_log.txt") == True:
        os.remove(path + "error_log.txt")
        
    if os.path.isfile(path + "Heat.db") == False:
        columns = ("data", "godzina", "temp_dot", "temp_comma", "jednostka")
        thread.Table_Maker_thread("Heat.db", columns, "temperatura") 
        print("Created")
           

    if os.path.isfile(path + "config.json") == False:
        dictionary = {
            "api_key": input("ENTER api_key from https://home.openweathermap.org/api_keys \n"),
            "base_url": "http://api.openweathermap.org/data/2.5/weather?",
            "localization_url": "http://ipinfo.io/json",
            "city": "",
            "temp_outside": "",
            "current_pressure": "",
            "current_humidity": "",
            "info_weather": "",
            "IP_query": "",
            "color": "",
            "brightness": 0.5,
            "effects": 0,
            "leds_speed": 1,
            "hour_start_LCD": 8,
            "hour_stop_LCD": 22,
            "time_update": str(datetime.datetime.now())
        } 
        ConfigControl.insert_Config(data=dictionary)
    data = [("color", 0), ("effects", 0)]
    ConfigControl.edit_Config(data)  


if __name__ == '__main__':
    startingProces()
    thread.thread_Control_thread()  # !!!!
    setproctitle.setproctitle("Emsii_LCD")