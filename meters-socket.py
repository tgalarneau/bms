#!/usr/bin/python3

#	Copyright 2020 Michael Janke
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>
#
#	Inspiration and data format credit to Stuart Wilde via this forum post:
#		https://www.irv2.com/forums/f54/thornwave-battery-monitor-375463.html#post4215155
#
#	2020-08-05	V 0.1 - Initial
#	2021-01-23	V 0.2 - Swtich from gatttool to bluepy
#
#	Reads characteristic 0x15 from Thornwave Bluetooth Battery Monitor 
#	Outputs in various formats
#
# 	Data format for Thornwave characteristic 0x15
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
#
#	Example:
#	b'\xe0\xff\x0f\xc8;X\\A\xd7;\\A\x8a\xb1\x90=\xe2\x14y?B\xd7\xcf\xc0Lk\xfb\xff\xff\xff\xff\xff\x93\xa7\xff\xff\xff\xff\xff\xff\x0eS\x85\x00 \xcen\x10i\x85\xc4A'
#
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
group = parser.add_mutually_exclusive_group()
parser.add_argument("-b", "--BLEaddress", help="BT DCPM BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="Interval query", required=True)
parser.add_argument("-m", "--meter", help="Meter type", required=True)
args = parser.parse_args()
z = args.interval
meter = args.meter   

class StatsReporter:
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
    print('attempting to connect')		
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

reporter = StatsReporter(
    (socket.AF_UNIX, ),
    '/tmp/telegraf.sock',
    socket.SOCK_DGRAM)

atexit.register(reporter.close_socket)

while True:
	result = p.readCharacteristic(0x15)
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

