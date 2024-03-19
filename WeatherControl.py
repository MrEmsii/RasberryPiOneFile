# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import Another

import requests, json 

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

def weather(city, api_key, base_url):
    try:
        complete_url = base_url + "appid=" + api_key + "&q=" + city + "&lang=pl" + "&units=metric"
        response = requests.get(complete_url)
        x = response.json()
        if x["cod"] != "404":
            y = x["main"]
            temp_outside = str(y["temp"]) + chr(223) + "C" + " / " + str(y["feels_like"]) + chr(223) + "C "
            current_pressure = str(y["pressure"]) +" hPa"
            current_humidity = str(y["humidity"]) + "%"
            z = x["weather"]
            info_weather = z[0]["description"]
            info_weather = Another.remove_Accents(input_text = info_weather)
    except:
        temp_outside = "NO INFO"
        current_pressure = "NO INFO"
        current_humidity = "NO INFO"
        info_weather = "NO INFO"
    return [("temp_outside",temp_outside),("current_pressure",current_pressure),("current_humidity",current_humidity),("info_weather",info_weather)]

def localization(url):
    try:
        r = requests.get(url)
        data = json.loads(r.content.decode())
        city = data["city"]
        ip_query = data["query"]
        return city, ip_query
    except:
        return "NO INFO"