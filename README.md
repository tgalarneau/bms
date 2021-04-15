# bms
JDB and Thornwave data monitoring

This project is for using bluetooth (bluepy) for fetching data from a JBD BMS (Overkill) and formatting it as cvs data and writing it to a unix socket for Telegraf through its listening socket plugin. It is then preceeds to Influxdb and Grafana for graphing.

The JBD BMS uses bluetooth to broadcast its data. The way this is handled is not standard as in just reading data or turning on notifications.

It requires sending a no data write request, to handles (0x03, 0x04, or 0x05). These messages cause the device to return a single notification response via a different handle. The returned notify is broken into 2 messages. The first is the begining of the message and the second is the last half.

So far I have only programmed the 0x03 (pack info) and 0x04 (cell voltages). I may expand this for the eprom settings at 0x05.

I also have to Thornwave bluetooth battery monitors. One for the solar charge controller and the other for an inverter. These are much simplier as it only requires and a readCharacteristic(0x15) and returns the data. 

The program is with the MAC address, collection interval and monitor name - bms.py -b xx:xx:xx:xx:xx -i 10 -m jbdbms.

I'm running this on a Raspberry Pi Zero W and used Python 3.9 for this.

