# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!

import json
import Another

file = "config.json"

@Another.save_error_to_file("error_log.txt")
def insert_Config(path, data):
    with open(str(path+file), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def edit_Config(path, data_list):
    with open(str(path+file), 'r+') as f:
        data = json.load(f)
        for row in data_list:
            data[row[0]] = row[1] # <--- add `id` value.
        f.seek(0)        # <--- should reset file position to the beginning.
        json.dump(data, f, indent=4)
        f.truncate()     # remove remaining part

def collect_Config(path, name):
    try:
        with open(str(path+file), 'r') as openfile:
            json_object = json.load(openfile)
        return json_object[str(name)]
    except FileNotFoundError:
        print("UPS!")
    except json.decoder.JSONDecodeError:
        collect_Config(path, name)