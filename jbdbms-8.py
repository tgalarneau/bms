#!/usr/bin/env python3

	# using python 3.9 
	
from bluepy.btle import Peripheral, DefaultDelegate, BTLEException
import struct
import argparse
import sys
import time
import binascii
import socket
import atexit
  
 	# Command line arguments
parser = argparse.ArgumentParser(description='BMS. fetches and outputs JBD bms data')
parser.add_argument("-b", "--BLEaddress", help="Device BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="Data fetch interval", required=True)
parser.add_argument("-m", "--meter", help="meter name", required=True)
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
            #sock = socket.socket(*self._socket_type,self._socket_data)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.connect("/tmp/telegraf.sock")
            self._sock = sock
            print('Created socket')
        except socket.error as e:
            print(f'Error creating socket: {e}')

    def close_socket(self):
        try:
            self._sock.close()
            print('Closed socket')
        except (AttributeError, socket.error) as e:
            print(f'Error closing socket: {e}')
    
    def send_data(self, data):
        try:
            sent = self._sock.send(data.encode(self._encoding))
            print(data)
        except (AttributeError, socket.error) as e:
            print(f'Error sending data on socket: {e}')
            # attempt to recreate socket on error
            self.close_socket()
            self.create_socket()

def cellinfo(data):			# process pack info
    infodata = data
    if infodata.find('dd03001b') != -1 and len(infodata) == 40:
        infodata = (infodata.removeprefix("dd03001b"))
        infodata = (binascii.unhexlify(infodata))
        i = 0
        volts, amps, remain, capacity, cycles, mdate, balance1, balance2 = struct.unpack_from('>HhHHHHHH', infodata, i)
        volts=volts/100
        amps = amps/100
        capacity = capacity/100
        remain = remain/100
        watts = volts*amps  							# adding watts field for dbase
        bal1 = (format(balance1, "b").zfill(16))		
        c16 = int(bal1[0:1])							
        c15 = int(bal1[1:2])							# using balance1 bits for 16 cells
        c14 = int(bal1[2:3])							# balance2 is for next 17-32 cells - not using
        c13 = int(bal1[3:4])
        c12 = int(bal1[4:5])							# bit shows (0,1) charging on-off
        c11 = int(bal1[5:6])
        c10 = int(bal1[6:7])
        c09 = int(bal1[7:8])
        c08 = int(bal1[8:9])
        c07 = int(bal1[9:10])
        c06 = int(bal1[10:11])
        c05 = int(bal1[11:12])
        c04 = int(bal1[12:13])        
        c03 = int(bal1[13:14])
        c02 = int(bal1[14:15])
        c01 = int(bal1[15:16])  
        message = ("meter,volts,amps,watts,remain,capacity,cycles\r\n%s,%0.2f,%0.2f,%0.2f,%0i,%0i,%0i" % (meter,volts,amps,watts,remain,capacity,cycles))		
        print(message)
        #reporter.send_data(message)             # not sending mdate (manufacture date)
        message = ("meter,c01,c02,c03,c04,c05,c06,c07,c08\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,c01,c02,c03,c04,c05,c06,c07,c08))
        print(message)
        #reporter.send_data(message)
    elif infodata.find('77') != -1 and len(infodata) == 28:	
        infodata = (infodata.removesuffix("77"))
        infodata = (binascii.unhexlify(infodata))
        i = 0
        protect,vers,percent,fet,cells,sensors,temp1,temp2 = struct.unpack_from('>HBBBBBHH', infodata, i)
        temp1 = (temp1-2731)/10
        temp2 = (temp2-2731)/10			# fet 0011 = 3 both on ; 0010 = 2 disch on ; 0001 = 1 chrg on ; 0000 = 0 both off
        prt = (format(protect, "b").zfill(16))		# protect trigger (0,1)(off,on)
        ovp = int(prt[0:1])			# overvoltage
        uvp = int(prt[1:2])			# undervoltage
        bov = int(prt[2:3])			# pack overvoltage
        buv = int(prt[3:4])			# pack undervoltage 
        cot = int(prt[4:5])			# current over temp
        cut = int(prt[5:6])			# current under temp
        dot = int(prt[6:7])			# discharge over temp
        dut = int(prt[7:8])			# discharge under temp
        coc = int(prt[8:9])			# charge over current
        duc = int(prt[9:10])		# discharge under current
        sc = int(prt[10:11])		# short circuit
        ic = int(prt[11:12])        # ic failure
        cnf = int(prt[12:13])		# fet config problem
        message = ("meter,ovp,uvp,bov,buv,cot,cut,dot,dut,coc,duc,sc,ic,cnf\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,ovp,uvp,bov,buv,cot,cut,dot,dut,coc,duc,sc,ic,cnf))
        print(message)
        #reporter.send_data(message)
        message = ("meter,protect,percent,fet,cells,temp1,temp2\r\n%s,%0000i,%00i,%00i,%0i,%0.1f,%0.1f" % (meter,protect,percent,fet,cells,temp1,temp2))
        print(message)
        #reporter.send_data(message)            # not sending version number or number of temp sensors
        
def cellvolts(data):			                # process cell voltages
    global cells1
    celldata = data
    if celldata.find('dd04') != -1 and len(celldata) == 40:
        celldata = (celldata.removeprefix("dd040010"))
        celldata = (binascii.unhexlify(celldata))
        i = 0
        cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8 = struct.unpack_from('>HHHHHHHH', celldata, i)
        cells1 = [cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8] 	# needed for max, min, delta calculations
        message = ("meter,cell1,cell2,cell3,cell4,cell5,cell6,cell7,cell8\r\n%s,%0i,%0i,%0i,%0i,%0i,%0i,%0i,%0i" % (meter,cell1,cell2,cell3,cell4,cell5,cell6,cell7,cell8))
        print(message)
        #reporter.send_data(message)
        cellmin = min(cells1)
        cellmax = max(cells1)
        delta = cellmax-cellmin
        message = ("meter,cellmin,cellmax,delta\r\n%s,%0i,%0i,%0i" % (meter,cellmin,cellmax,delta))
        print(message)
        #reporter.send_data(message)
                    
class MyDelegate(DefaultDelegate):		    # notification responses
	def __init__(self):
		DefaultDelegate.__init__(self)
	def handleNotification(self, cHandle, data):
		hex_data = binascii.hexlify(data) 		# Given raw bytes, get an ASCII string representing the hex values
		text_string = hex_data.decode('utf-8')
		if text_string.find('dd04') != -1:		# check incoming data for routing to decoding routines
			cellvolts(text_string)
		elif text_string.find('dd03') != -1:
			cellinfo(text_string)
		elif text_string.find('77') != -1 and len(text_string) == 38:	 # x04
			cellvolts(text_string)
		elif text_string.find('77') != -1 and len(text_string) == 28:	 # x03
			cellinfo(text_string)		
try:
    print('attempting to connect')		
    bms = Peripheral(args.BLEaddress,addrType="public")
except BTLEException as ex:
    time.sleep(10)
    print('2nd try connect')
    bms = Peripheral(args.BLEaddress,addrType="public")
except BTLEException as ex:
    print('cannot connect')
    exit()
else:
    print('connected ',args.BLEaddress)

bms.setDelegate(MyDelegate())		# setup delegate for notifications

reporter = StatsReporter(
    (socket.AF_UNIX, ),
    '/tmp/telegraf.sock',
    socket.SOCK_DGRAM)

atexit.register(reporter.close_socket)

		# write empty data to 0x15 for notification request   --  address x03 handle for info & x04 handle for cell voltage
		# using waitForNotifications(5) as less than 5 seconds has caused some missed notifications
while True:
	print('sending')
	result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x03\x00\xff\xfd\x77',False)		# write x03 w/o response cell info
	bms.waitForNotifications(5)
	result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x04\x00\xff\xfc\x77',False)		# write x04 w/o response cell voltages
	bms.waitForNotifications(5)
	time.sleep(z)
   