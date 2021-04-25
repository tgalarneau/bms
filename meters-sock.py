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
#from datetime import datetime
#from datetime import timedelta
from bluepy.btle import Peripheral, BTLEException

# Slurp up command line arguments
__author__ = 'Michael Janke'
parser = argparse.ArgumentParser(description='Thornwave BT DCPM slurper. Reads and outputs BT DCPM data')
group = parser.add_mutually_exclusive_group()
parser.add_argument("-b", "--BLEaddress", help="BT DCPM BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="Interval query", required=True)
parser.add_argument("-m", "--meter", help="Meter type", required=True)
parser.add_argument("-v", "--verbose", help="debug output", action="store_true")

args = parser.parse_args()

#The file handler for the Telegraf process.
telegraf_socket = "/tmp/telegraf.sock"

# Connection to Telegraf, over a network socket.
#sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
#sock.connect(telegraf_socket)

# Connect to thornwave. Try twice, then fail 
try:
  p = Peripheral(args.BLEaddress, addrType="random")

except BTLEException as ex:
  if args.verbose:
    print("Read failed. ", ex)
  time.sleep(10)
  try:
     p = Peripheral(args.BLEaddress, addrType="random")
  except:
     if args.verbose:
       print("Read failed. ", ex)
     exit
else:
  result=p.readCharacteristic(0x15)
  if args.verbose:
    print(result)

  #delta = str(timedelta(seconds=TimeSinceStart))
         
z = args.interval
meter = args.meter         
         
while True:
	result = p.readCharacteristic(0x15)
# Unpack into variables, skipping bytes 0-2
	i = 3
	PctCharged, V1Volts, V2Volts,Current, Power, Temperature, PowerMeter, ChargeMeter, TimeSinceStart, CurrentTime, PeakCurrent = struct.unpack_from('<BfffffqqIIf', result, i)
	if args.verbose:
		print(PctCharged, V1Volts, V2Volts, Current, Power, Temperature, PowerMeter, ChargeMeter, TimeSinceStart, Currentime, PeakCurrent)
# Clean up vars
	PctCharged = PctCharged/2
	PowerMeter = PowerMeter/1000
	ChargeMeter = ChargeMeter/1000
	
# Format and send message to socket - not sending V2Volts, TimeSinceStart, Currentime 
	message = ("meter,volts,amps,watts,temp,kwh,ah,peak\r\n%s,%0.3f,%0.2f,%0.2f,%0.1f,%0.4f,%0.2f,%0.2f" % (meter,V1Volts,Current,Power,Temperature,PowerMeter,ChargeMeter,PeakCurrent))
	print(message)
	#sock.send(message.encode('utf8'))
	time.sleep(z)

