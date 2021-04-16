#!/usr/bin/env python3

	# using python 3.9 
	
import bluepy
import bluepy.btle as btle
import struct
import argparse
import sys
import time
import binascii
import socket
import signal
  
 # Command line arguments
parser = argparse.ArgumentParser(description='BMS. Writes and receives notify and output data')
group = parser.add_mutually_exclusive_group()
parser.add_argument("-b", "--BLEaddress", help="BT BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="data interval", required=True)
parser.add_argument("-m", "--meter", help="Meter name", required=True)
args = parser.parse_args() 

def signal_handler(signal, frame):
    print('Stopping...')
    sock.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# The file handler for the Telegraf process.
telegraf_socket = "/tmp/telegraf.sock"

# Connection to Telegraf, over a network socket.
#sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
#sock.connect(telegraf_socket)

def cellinfo(data):
	infodata = data
	if infodata.find('dd03001f') != -1:
		infodata = (infodata.removeprefix("dd03001f"))
		infodata = (binascii.unhexlify(infodata))
		i = 0
		volts, amps, remain, capacity, cycles, mdate, balance1, balance2 = struct.unpack_from('>HhHHHHHH', infodata, i)
		volts=volts/100
		amps = amps/100
		capacity = capacity/100
		remain = remain/100
		watts = volts*amps  	# adding watts field for dbase
						    
		bal1 = (format(balance1, "b").zfill(16))      # using balance1 bits for 16 cells - (balance2 is for next 17-32 cells)
		c01 = int(bal1[0:1])
		c02 = int(bal1[1:2])
		c03 = int(bal1[2:3])
		c04 = int(bal1[3:4])
		c05 = int(bal1[4:5])
		c06 = int(bal1[5:6])
		c07 = int(bal1[6:7])
		c08 = int(bal1[7:8])
		c09 = int(bal1[8:9])
		c10 = int(bal1[9:10])
		c11 = int(bal1[10:11])
		c12 = int(bal1[11:12])
		c13 = int(bal1[12:13])        
		c14 = int(bal1[13:14])
		c15 = int(bal1[14:15])
		c16 = int(bal1[15:16])   
				
		message = ("meter,volts,amps,watts,remain,capacity,cycles\r\n%s,%0.2f,%0.2f,%0.2f,%0i,%0i,%0i,%0i,%0i" % (meter,volts,watts,amps,remain,capacity))
		print(message)
		#sock.send(message.encode('utf8'))		# not sending mdate (manfacture date)
		message = ("meter,c01,c02,c03,c04,c05,c06,c07,c08\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,c01,c02,c03,c04,c05,c06,c07,c08))
		print(message)
		#sock.send(message.encode('utf8'))
		message = ("meter,c09,c10,c11,c12,c13,c14,c15,c16\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,c09,c10,c11,c12,c13,c14,c15,c16))
		print(message)
		#sock.send(message.encode('utf8'))

	elif infodata.find('77') != -1 and len(infodata) == 36:	
		infodata = (infodata.removesuffix("77"))
		infodata = (binascii.unhexlify(infodata))
		i = 0
		protect,vers,percent,fet,cells,sensors,temp1,temp2,temp3,temp4 = struct.unpack_from('>HBBBBBHHHH', infodata, i)
		temp1 = (temp1-2731)/10
		temp2 = (temp2-2731)/10					# fet 0011 = 3  both on - 0010 = 2 disch on - 0001 = 1 chrg on - 0000 = 0 both off
		temp3 = (temp3-2731)/10
		temp4 = (temp4-2731)/10
		message = ("meter,protect,percent,cells,temp1,temp2,temp3,temp4\r\n%s,%0000i,%00i,%00i,%0.1f,%0.1f,%0.1f,%0.1f" % (meter,protect,percent,fet,cells,temp1,temp2,temp3,temp4))
		print(message)
		#sock.send(message.encode('utf8'))          # not sending version number or number of temp sensors

def cellvolts(data):
	celldata = data
	if celldata.find('dd04') != -1:
		celldata = (celldata.removeprefix("dd040020"))
		celldata = (binascii.unhexlify(celldata))
		i = 0
		cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8 = struct.unpack_from('>HHHHHHHH', celldata, i)
		message = ("meter,cell1,cell2,cell3,cell4,cell5,cell6,cell7,cell8\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,cell1,cell2,cell3,cell4,cell5,cell6,cell7,cell8))
		print(message)
		#sock.send(message.encode('utf8')
	elif celldata.find('77') != -1 and len(celldata) == 38:
		celldata = (celldata.removesuffix("77"))
		celldata = (binascii.unhexlify(celldata))
		i = 0
		cell9, cell10, cell11, cell12, cell13, cell14, cell15, cell16 = struct.unpack_from('>HHHHHHHH', celldata, i)
		message = ("meter,cell9,cell10,cell11,cell12,cell13,cell14,cell15,cell16\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,cell9,cell10,cell11,cell12,cell13,cell14,cell15,cell16))
		print(message)
		#sock.send(message.encode('utf8'))

class MyDelegate(btle.DefaultDelegate):
	def __init__(self):
		btle.DefaultDelegate.__init__(self)
	def handleNotification(self, cHandle, data):
		# Given raw bytes, get an ASCII string representing the hex values
		hex_data = binascii.hexlify(data) 
		text_string = hex_data.decode('utf-8')
		# check incoming data for routing to decoding routines
		if text_string.find('dd04') != -1:
			cellvolts(text_string)
		elif text_string.find('dd03') != -1:
			cellinfo(text_string)
		elif text_string.find('77') != -1 and len(text_string) == 38:	 # x04
			cellvolts(text_string)
		elif text_string.find('77') != -1 and len(text_string) == 36:	 # x03
			cellinfo(text_string)		

# Connect to bms. Try twice, then fail 
try:
	bms = bluepy.btle.Peripheral(args.BLEaddress)
except BTLEException as ex:
	time.sleep(10)
	bms = bluepy.btle.Peripheral('A4:C1:38:FF:95:BE')

z = args.interval
meter = args.meter		
bms.setDelegate(MyDelegate())

while True:
# write empty data to 0x15 for notification request   --  address x03 handle for info & x04 handle for cell voltage
	result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x03\x00\xff\xfd\x77',False)
	bms.waitForNotifications(1)
	result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x04\x00\xff\xfc\x77',False)
	bms.waitForNotifications(1)
	time.sleep(z)
   
