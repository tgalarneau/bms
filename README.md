# bms
JBD BMS and Thornwave bluetooth data monitoring 

This project is for using bluetooth (bluepy) for fetching data from a JBD BMS or Overkill BMS and formatting it to cvs data and writing it to a unix socket for Telegraf's Socket Listener Input Plugin. The data then preceeds to Influxdb and Grafana for graphing.

The JBD BMS uses serial or bluetooth to access its data. This project is for the bluetooth interface. The way this is done is not standard as in just reading requests or turning on notifications to receive ongoing data.

It requires sending without data, write requests to handles (0x03 and 0x04), i.e. 'dda50400fffc77'. These messages cause the device to return a single notification response via a different handle. The returned notify is broken into 2 messages. The first is the start of the message and the second is the last half. 

So far I have only programmed the 0x03 (pack info) and 0x04 (cell voltages) for system monitoring.

I also use two Thornwave bluetooth battery monitors. One for the solar charge controller and the other for an inverter. These are much simpler only requiring a read request at (0x15) which returns the data for processing.

The program is initiated with a MAC address (-b), collection interval (-i) and monitor name (-m).

bms.py -b xx:xx:xx:xx:xx -i 10 -m jbdbms.

I'm running this on a RaspberryPi Zero W and used Python 3.9. As Debian only has version 3.7, it required building 3.9 from source. This was only necessary because (In Python 3.9, new string methods removeprefix() and removesuffix() are introduced) and was too lazy to revert to earlier method.

![Screenshot](jbdbms.png)

For Thornwave data see https://github.com/mkjanke/ThornwavePy I have only modified it for cvs data, writing to Unix socket and leaving connection open for ongoing data. As I am using linux I am utilizing systemd services for the data collection, with automatic loading on startup and restarting if connection lost.

![Screenshot](thornwave.png)

The meters-sock.py is for the Thronwave meters. For the JBD bms data only - bms.py alone is required. Just discover your JBD mac address. I use hcitool lescan to find this or the Xiaoxiang app also shows this at startup. The program only prints out the data for testing until the sock commands are uncommented and Telegraf is setup on the sock to deliver it to influxdb. 

I have only tested and used with linux but this should be okay from any python ready laptop within bluetooth range. I use the RaspberryPi zero W for 24/7 use and proximity to device bluetooth signal.
