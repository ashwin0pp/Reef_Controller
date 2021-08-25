import sys
import time
import datetime
import csv
import re
import smbus
from ctypes import c_short
from ctypes import c_byte
from ctypes import c_ubyte
import requests, json
import cayenne.client
from AtlasI2C import AtlasI2C
DEVICEa = 0x77 # Default device I2C address
bus = smbus.SMBus(1) # Rev 2 Pi, Pi 2 & Pi 3 uses bus 1
                     # Rev 1 Pi uses bus 0
def currentweather():
    api_key="fe88435d6a48e5dd328cb0a30171c67f"
    base_url="http://api.openweathermap.org/data/2.5/weather?"
    city_name="Ann Arbor"
    complete_url=base_url+"q="+city_name+"&appid="+api_key
    response=requests.get(complete_url)
    x=response.json()
    y=x["main"]
    current_temperature=((y["temp"])-273.15)*(9/5)+32
    current_temperature_frmt=format(current_temperature,'.2f')
    current_temperature_frmt=float(current_temperature_frmt)
    current_pressure=(y["pressure"])*0.029529983071445
    current_pressure_frmt=format(current_pressure,'.2f')
    current_pressure_frmt=float(current_pressure_frmt)
    current_humidity=float(y["humidity"])
    z=x["weather"]
    weather_description=str(z[0]["description"])
    weatherdata=[current_temperature_frmt,current_pressure_frmt,current_humidity,weather_description]
    return weatherdata
def get_devices():
    device = AtlasI2C()
    device_address_list = device.list_i2c_devices()
    device_address_list = device_address_list[0:5]
    device_list = []
    for i in device_address_list:
        device.set_i2c_address(i)
        response = device.query("I")
        moduletype = response.split(",")[1]
        response = device.query("name,?").split(",")[1]
        device_list.append(AtlasI2C(address = i, moduletype = moduletype, name = response))
    return device_list
def sensor_readout():
    #######################################
    #Send write command to all the devices
    #######################################
    for dev in device_list:
        dev.write("R")
    time.sleep(delaytime)
    #######################################
    #Get PH and temp readout from the board
    #######################################
    ph = device_list[1]
    ph = ph.read()
    temp = device_list[3]
    temp = temp.read()
    sal = device_list[2]
    sal = sal.read()
    orp = device_list[0]
    orp = orp.read()
    co2 = device_list[4]
    co2 = co2.read()
    sensor_readout=[ph,temp,sal,orp,co2]
    return sensor_readout
def cleanup(ph,temp,sal,orp,co2):
    ph = re.findall(':\s+\S+', ph)
    ph = ph[0]
    ph = ph[2:7]
    temp = re.findall(':\s+\S+', temp)
    temp = temp[0]
    temp = temp[2:7]
    sal = re.findall(':\s+\S+', sal)
    sal = sal[0]
    sal = sal[2:7]
    orp = re.findall(':\s+\S+', orp)
    orp = orp[0]
    orp = orp[2:7]
    co2 = re.findall(':\s+\S+', co2)
    co2 = co2[0]
    co2 = co2[2:5]
    cleanup_value=[ph,temp,sal,orp,co2]
    return cleanup_value

def getShort(data, index):
  # return two bytes from data as a signed 16-bit value
  return c_short((data[index+1] << 8) + data[index]).value

def getUShort(data, index):
  # return two bytes from data as an unsigned 16-bit value
  return (data[index+1] << 8) + data[index]

def getChar(data,index):
  # return one byte from data as a signed char
  result = data[index]
  if result > 127:
    result -= 256
  return result

def getUChar(data,index):
  # return one byte from data as an unsigned char
  result =  data[index] & 0xFF
  return result

def readBME280ID(addr=DEVICEa):
  # Chip ID Register Address
  REG_ID     = 0xD0
  (chip_id, chip_version) = bus.read_i2c_block_data(addr, REG_ID, 2)
  return (chip_id, chip_version)

def readBME280All(addr=DEVICEa):
  # Register Addresses
  REG_DATA = 0xF7
  REG_CONTROL = 0xF4
  REG_CONFIG  = 0xF5

  REG_CONTROL_HUM = 0xF2
  REG_HUM_MSB = 0xFD
  REG_HUM_LSB = 0xFE

  # Oversample setting - page 27
  OVERSAMPLE_TEMP = 2
  OVERSAMPLE_PRES = 2
  MODE = 1

  # Oversample setting for humidity register - page 26
  OVERSAMPLE_HUM = 2
  bus.write_byte_data(addr, REG_CONTROL_HUM, OVERSAMPLE_HUM)

  control = OVERSAMPLE_TEMP<<5 | OVERSAMPLE_PRES<<2 | MODE
  bus.write_byte_data(addr, REG_CONTROL, control)

  # Read blocks of calibration data from EEPROM
  # See Page 22 data sheet
  cal1 = bus.read_i2c_block_data(addr, 0x88, 24)
  cal2 = bus.read_i2c_block_data(addr, 0xA1, 1)
  cal3 = bus.read_i2c_block_data(addr, 0xE1, 7)

  # Convert byte data to word values
  dig_T1 = getUShort(cal1, 0)
  dig_T2 = getShort(cal1, 2)
  dig_T3 = getShort(cal1, 4)

  dig_P1 = getUShort(cal1, 6)
  dig_P2 = getShort(cal1, 8)
  dig_P3 = getShort(cal1, 10)
  dig_P4 = getShort(cal1, 12)
  dig_P5 = getShort(cal1, 14)
  dig_P6 = getShort(cal1, 16)
  dig_P7 = getShort(cal1, 18)
  dig_P8 = getShort(cal1, 20)
  dig_P9 = getShort(cal1, 22)

  dig_H1 = getUChar(cal2, 0)
  dig_H2 = getShort(cal3, 0)
  dig_H3 = getUChar(cal3, 2)

  dig_H4 = getChar(cal3, 3)
  dig_H4 = (dig_H4 << 24) >> 20
  dig_H4 = dig_H4 | (getChar(cal3, 4) & 0x0F)

  dig_H5 = getChar(cal3, 5)
  dig_H5 = (dig_H5 << 24) >> 20
  dig_H5 = dig_H5 | (getUChar(cal3, 4) >> 4 & 0x0F)

  dig_H6 = getChar(cal3, 6)

  # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
  wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + ((2.3 * OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM)+0.575)
  time.sleep(wait_time/1000)  # Wait the required time  

  # Read temperature/pressure/humidity
  data = bus.read_i2c_block_data(addr, REG_DATA, 8)
  pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
  temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
  hum_raw = (data[6] << 8) | data[7]

  #Refine temperature
  var1 = ((((temp_raw>>3)-(dig_T1<<1)))*(dig_T2)) >> 11
  var2 = (((((temp_raw>>4) - (dig_T1)) * ((temp_raw>>4) - (dig_T1))) >> 12) * (dig_T3)) >> 14
  t_fine = var1+var2
  temperature = float(((t_fine * 5) + 128) >> 8);

  # Refine pressure and adjust for temperature
  var1 = t_fine / 2.0 - 64000.0
  var2 = var1 * var1 * dig_P6 / 32768.0
  var2 = var2 + var1 * dig_P5 * 2.0
  var2 = var2 / 4.0 + dig_P4 * 65536.0
  var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
  var1 = (1.0 + var1 / 32768.0) * dig_P1
  if var1 == 0:
    pressure=0
  else:
    pressure = 1048576.0 - pres_raw
    pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
    var1 = dig_P9 * pressure * pressure / 2147483648.0
    var2 = pressure * dig_P8 / 32768.0
    pressure = pressure + (var1 + var2 + dig_P7) / 16.0

  # Refine humidity
  humidity = t_fine - 76800.0
  humidity = (hum_raw - (dig_H4 * 64.0 + dig_H5 / 16384.0 * humidity)) * (dig_H2 / 65536.0 * (1.0 + dig_H6 / 67108864.0 * humidity * (1.0 + dig_H3 / 67108864.0 * humidity)))
  humidity = humidity * (1.0 - dig_H1 * humidity / 524288.0)
  if humidity > 100:
    humidity = 100
  elif humidity < 0:
    humidity = 0

  return temperature/100.0,pressure/100.0,humidity

def ambientweather():
    temperature_ambient,pressure_ambient,humidity_ambient = readBME280All()
    ambient_weather_values = [temperature_ambient,pressure_ambient,humidity_ambient]
    return ambient_weather_values

########################################
# Cayenne authentication info. 
#This should be obtained from the 
#Cayenne Dashboard.
########################################
MQTT_USERNAME  = "ENTER USERNAME"
MQTT_PASSWORD  = "ENTER PASSWORD"
MQTT_CLIENT_ID = "ENTER CLIENT ID"
client = cayenne.client.CayenneMQTTClient()
client.begin(MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID)
########################################

########################################
#GLOBAL VARIABLES
########################################
currentweather1=[0,0,0,'abc']
cleanup_values=[0,0,0,0,0]
sensor_readouts=[0,0,0,0,0]
########################################

device_list = get_devices()
device = device_list[0]
delaytime = device.long_timeout
    
while True:
    ########################################
    #SENSOR READOUTS
    ########################################
    sensor_readouts=sensor_readout()
    ph=sensor_readouts[0]
    temp=sensor_readouts[1]
    sal=sensor_readouts[2]
    orp=sensor_readouts[3]
    co2=sensor_readouts[4]
    ########################################
    #DATA CLEANUP
    ########################################
    cleanup_values=cleanup(ph,temp,sal,orp,co2)
    ph=cleanup_values[0]
    temp=cleanup_values[1]
    sal=cleanup_values[2]
    orp=cleanup_values[3]
    co2=cleanup_values[4]
    try:
        co2=int(co2)
    except:
        co2=0
    ########################################
    #AMBIENT WEATHER
    ########################################
    a_w_values=ambientweather()
    temp_a=a_w_values[0]
    temp_a=(temp_a*1.8)+32
    temp_a=float(temp_a)
    temp_a=format(temp_a,'.2f')
    pres_a=a_w_values[1]
    pres_a=pres_a*0.029529983071445
    pres_a=float(pres_a)
    pres_a=format(pres_a,'.2f')
    hum_a=a_w_values[2]
    hum_a=float(hum_a)
    hum_a=format(hum_a,'.2f')
    ########################################
    #CURRENT DATE & TIME
    ########################################
    daten=str(datetime.datetime.now().strftime("%m-%d-%Y"))
    timen=str(datetime.datetime.now().strftime("%H:%M:%S"))
    timecheck=datetime.datetime.now()
    itime=timecheck.strftime("%S")
    itime=int(itime)
    timerange=[5,10,15,20,25,30,35,40,45,50]
    if itime in timerange:
        currentweather1=currentweather()
    ########################################
    #CREATE CSV FILE
    #######################################
    fllce = "/home/pi/Desktop/BOOT/SENSOR READINGS/sensor_readings "+ daten+".csv"
    flnme = "sensor_readings "+ daten
    tempo=currentweather1[0]
    presso=currentweather1[1]
    humo=currentweather1[2]
    weathero=currentweather1[3]
    with open(fllce, mode='a') as flnme:
        snsr=csv.writer(flnme, delimiter=',',quotechar='"',quoting=csv.QUOTE_MINIMAL)
        snsr.writerow([daten,timen,temp,ph,sal,orp,co2,tempo,presso,humo,weathero,temp_a,pres_a,hum_a])
    ########################################
    #Post data to Cayenne
    #######################################
    client.loop()
    client.celsiusWrite(1, temp)
    client.luxWrite(2, ph)
    client.luxWrite(3, sal)
    client.luxWrite(4, orp)
    client.luxWrite(5, co2)
    #a=[daten,timen,temp,ph,sal,orp,co2,tempo,presso,humo,weathero,temp_a,pres_a,hum_a]
    #print(a)
    
