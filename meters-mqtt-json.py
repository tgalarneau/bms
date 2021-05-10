#!/usr/bin/python3

import argparse
import struct
import time
import atexit
import json
from bluepy.btle import Peripheral, BTLEException
import paho.mqtt.client as paho

# Command line arguments
parser = argparse.ArgumentParser(description='Thornwave bluetooth. Reads and outputs data')
parser.add_argument("-b", "--BLEaddress", help="BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="time interval to fetch", required=True)
parser.add_argument("-m", "--meter", help="meter name", required=True)
args = parser.parse_args()
z = args.interval
meter = args.meter   

broker="127.0.0.1"
port=1883
topic = "data/"+meter

def disconnect():
    mqtt.disconnect()
    print("broker disconnected")
  
try:
    print('connecting BT')		                        #  bluetooth connection
    p = Peripheral(args.BLEaddress,addrType="random")
except BTLEException as ex:
    time.sleep(10)
    print('2nd try connect')
    p = Peripheral(args.BLEaddress,addrType="random")
except BTLEException as ex:
    print('cannot connect')
    exit()
else:
    print('connected ',args.BLEaddress)

atexit.register(disconnect)

if meter == "solar":
    mqtt = paho.Client("control1")                     #create and connect client
elif meter == "inverter":
    mqtt = paho.Client("control2")

mqtt.connect(broker,port) 

while True:
    result = p.readCharacteristic(0x15)     # bluetoon fetch and send to socket
        # Unpack into variables, skipping bytes 0-2
    i = 3
    PctCharged, V1Volts, V2Volts,Current, Power, Temperature, PowerMeter, ChargeMeter, TimeSinceStart, CurrentTime, PeakCurrent = struct.unpack_from('<BfffffqqIIf', result, i)
	    # Clean up vars
    PctCharged = PctCharged/2
    PowerMeter = PowerMeter/1000
    ChargeMeter = ChargeMeter/1000
        # Format and send mqtt message - not sending V2Volts, TimeSinceStart, Currentime as influxdb as timestamp
    message = {
        "meter":meter,
        "volts": V1Volts,
        "amps": Current,
        "watts": Power, 
        "temp": Temperature, 
        "kwh": PowerMeter, 
        "ah": ChargeMeter,
        "peak": PeakCurrent 
    }
    ret = mqtt.publish(topic, payload=json.dumps(message), qos=0, retain=False)
    time.sleep(z)
