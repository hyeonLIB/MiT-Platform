"""
editor : hyeonLIB
os : ubuntu 20.04
python version : 3.8
"""

import os
import time
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import argparse
import paho.mqtt.client as paho
import sql_function
import hrosad_offline
# import rhrad_offline

parser = argparse.ArgumentParser(description='function for postgresql')
parser.add_argument('--ip',default = '203.255.56.50', metavar='', help ='ip x of database server')
parser.add_argument('--pw',metavar='',default = 'sselab0812!', help ='password for database')
args = parser.parse_args()

global ip_address, password
ip_address = args.ip
password = args.pw

# ip_address = '203.255.56.50'
# password = 'sselab0812!'

"""
## extract data of each person (interval = 1 month)
## data sampling by timestamp -> 1 minute
## execute anomaly detection
## post anomaly points from csv files made be anomaly detection, key=anomaly_points ++ hros, rhr interpolated ones 
   -> mqtt library and add logs
"""

def extract_hrsteps(device_id):
    sql = 'SELECT * FROM ts_kv_dictionary;'
    keys = sql_function.extractData(sql, database_name='thingsboard')
    key_hr = keys[keys['key']=='heart_rate']['key_id'].item()
    key_steps = keys[keys['key']=='steps']['key_id'].item()

    sql = f"SELECT ts, long_v FROM ts_kv WHERE entity_id = '{device_id}' AND key = {key_hr};"  # + AND timestamp ?
    hr_data = sql_function.extractData(sql, database_name='thingsboard')
    sql = f"SELECT ts, long_v FROM ts_kv WHERE entity_id = '{device_id}' AND key = {key_hr};"
    steps_data = sql_function.extractData(sql, database_name='thingsboard')

    return hr_data, steps_data


# data sampling by timestamp -> 1 minute
def down_sampling(time, hr_data, steps_data):
    hr_data = hr_data.set_index(pd.to_datetime(hr_data['ts'], unit='ms')) 
    steps_data = steps_data.set_index(pd.to_datetime(steps_data['ts'], unit='ms'))
    hr_data['heartrate'] = hr_data['long_v'] 
    hr_data = hr_data.drop(columns=['long_v','ts'])
    steps_data['steps'] = steps_data['long_v'] 
    steps_data = steps_data.drop(columns=['long_v','ts'])
    hr_data = hr_data.resample(time).mean()
    steps_data = steps_data.resample(time).sum() # I'm not sure that it is accurate

    return hr_data, steps_data


# execute anomaly detection
def anomaly_detection(hr_data, steps_data):
    # try:
    model = hrosad_offline.HROSAD_offline()
    df1 = model.HROS(hr_data, steps_data)
    df2 = model.pre_processing(df1)
    sdHR = df2[['heartrate']]
    sdSteps = df2[['steps']]
    data_seasnCorec = model.seasonality_correction(sdHR, sdSteps)
    data_seasnCorec += 0.1
    std_data = model.standardization(data_seasnCorec)
    data = model.anomaly_detection(std_data)
    model.visualize(data)
    # except:
    #     print("Error has been occured while detecting anomalies")

# post anomaly points from csv files made by anomaly detection
# def


# log function
# def


# plot capturing
# def


# mqtt tools
def mqtt_message(device_id, ACCESS_TOKEN, message):
    try:
        """
        tools to send the result to server
        """
        broker=ip_address
        port=1883 

        def on_publish(client,userdata,result):
            print(f"{device_id} - Has been connected successfully \n")
            pass

        client1= paho.Client("control")
        client1.on_publish = on_publish
        client1.username_pw_set(ACCESS_TOKEN)
        client1.connect(broker,port)
        client1.publish("v1/devices/me/telemetry",message) #topic-v1/devices/me/telemetry
        print(f"{device_id} - Abnormal points have been sent to the server \n")
    except:
        print("There's something wrong with network")


# def run()


# try except 
# def main(opt):
def main():
    try:
        ## extract data of each device in thingsboard database
        sql = 'SELECT device_id, credentials_id FROM device_credentials;' # list of devices
        devices_data = sql_function.extractData(sql, database_name='thingsboard')
        list_device_id = devices_data['device_id']
        list_token_key = devices_data['credentials_id']
    except:
        print("There's something wrong with PostgreSQL database")
    
    for device_id in list_device_id:
        hr_data, steps_data = extract_hrsteps(device_id)
        if hr_data.empty:
            pass
        else:
            try:
                print(device_id)
                sampling_rate = 'T'
                hr_data, steps_data = down_sampling(sampling_rate, hr_data, steps_data)
            except:
                print("Error has been occured while sampling")
            
            anomaly_detection(hr_data, steps_data)

            
        # MQTT
        # try:
        #     print("mqtt")
        # except:
        #     print("error")

        # LOG

# # message
# payload="{"
# payload+="\"Humidity\":60,"; 
# payload+="\"Temperature\":25"; 
# payload+="}"


if __name__ == "__main__":
    # opt = parse_opt()
    # main(opt)
    main()
