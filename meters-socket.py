#!/usr/bin/python3

#	Copyright 2020 Michael Janke
#
#       	 Struct
# 	Fields   Type      Desc
#
#	  0 - 2:  Unknown
#	  3    :  B         Pct Charged, LSB must be stripped
#	  7 - 4:  f         V1 volts, LSB, 32-bit float
#	 11 - 8:  f         V2 volts, LSB, 32-bit float
#	 15 - 12: f         Current (amps), LSB, 32-bit float
#	 19 - 16: f         Power (watts), LSB, 32-bit float
#	 23 - 20: f         Temperature (C), LSB, 32-bit float
#	 31 - 24: q         Power Meter (watts * 1000), 64-bit int
#	 39 - 32: q         Charge Meter (Amp-hours * 1000), 64-bit int
#	 43 - 40: I         Uptime (seconds), unsigned 32-bit int
#	 47 - 44: I         Date/Time (unknown format)
#	 51 - 48: f         Peak Current, 32-bit float
#	 52+    : Unknown

import argparse
import struct
import time
import sys
import signal
import atexit
import socket
from bluepy.btle import Peripheral, BTLEException

# Slurp up command line arguments
parser = argparse.ArgumentParser(description='Thornwave BT DCPM slurper. Reads and outputs BT DCPM data')
parser.add_argument("-b", "--BLEaddress", help="BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="time interval to fetch", required=True)
parser.add_argument("-m", "--meter", help="meter name", required=True)
args = parser.parse_args()
z = args.interval
meter = args.meter   

class StatsReporter:                    # socket routines
    def __init__(
        self,
        socket_type,
        socket_address,
        socket_data,
        encoding='utf-8',
    ):
        self._socket_type = socket_type
        self._socket_address = socket_address
        self._encoding = encoding
        self._socket_data = socket_data
        self.create_socket()
    
    def create_socket(self):
        try:
            sock = socket.socket(*self._socket_type,self._socket_data)
            #sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.connect("/tmp/telegraf.sock")
            self._sock = sock
            print('Created socket')
        except socket.error as e:
            print(f'Got error while creating socket: {e}')

    def close_socket(self):
        try:
            self._sock.close()
            print('Closed socket')
        except (AttributeError, socket.error) as e:
            print(f'Got error while closing socket: {e}')
    
    def send_data(self, data):
        try:
            sent = self._sock.send(data.encode(self._encoding))
            print(data)
        except (AttributeError, socket.error) as e:
            print(f'Got error while sending data on socket: {e}')
            # attempt to recreate socket on error
            self.close_socket()
            self.create_socket()

try:
    print('attempting to connect')		    #  bluetooth connection
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

reporter = StatsReporter(                   # intiate socket
    (socket.AF_UNIX, ),
    '/tmp/telegraf.sock',
    socket.SOCK_DGRAM)

atexit.register(reporter.close_socket)      # exit routine 

while True:
	result = p.readCharacteristic(0x15)     # bluetoon fetch and send to socket
# Unpack into variables, skipping bytes 0-2
	i = 3
	PctCharged, V1Volts, V2Volts,Current, Power, Temperature, PowerMeter, ChargeMeter, TimeSinceStart, CurrentTime, PeakCurrent = struct.unpack_from('<BfffffqqIIf', result, i)
	# Clean up vars
	PctCharged = PctCharged/2
	PowerMeter = PowerMeter/1000
	ChargeMeter = ChargeMeter/1000

# Format and send message to socket - not sending V2Volts, TimeSinceStart, Currentime as influxdb as timestamp
	message = ("meter,volts,amps,watts,temp,kwh,ah,peak\r\n%s,%0.3f,%0.2f,%0.2f,%0.1f,%0.4f,%0.2f,%0.2f" % (meter,V1Volts,Current,Power,Temperature,PowerMeter,ChargeMeter,PeakCurrent))
	#print(message)
	reporter.send_data(message)
	time.sleep(z)

