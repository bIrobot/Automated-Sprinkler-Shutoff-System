#!/usr/bin/env python

import configparser
import os
import time

import RPi.GPIO as GPIO  # Import GPIO library

import email_handler
import weather_handler


class sprinkler():

    def __init__(self):
        # Setup GPIO I/O pins
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(7, GPIO.OUT)  # This pin controls relay switch. When ON/True, watering is disabled. Default OFF
        GPIO.setup(11, GPIO.OUT)  # This pin controls a flashing red light that flashes when data error
        GPIO.setup(13, GPIO.OUT)  # This pin enables green light when watering
        GPIO.setup(15, GPIO.OUT)  # This pin enables red light when watering disabled

        self.api_key = ''
        self.latitude = ''
        self.longitude = ''
        self.precip_threshold = 0.6
        self.server = ''
        self.username = ''
        self.password = ''
        self.admin_email = ''

        self.sprinkler_enabled = True
        self.disabled_time = 0
        self.prev_time_weather = 0
        self.prev_time_email = 0

        self.load_config()
        self.weather = weather_handler.darkSky(self.api_key, self.latitude, self.longitude, self.checkIncrement, self.daysDisabled, self.precip_threshold)
        self.email = email_handler.emailHandler(self.server, 993, self.username, self.password, self.admin_email)

    def main(self):
        try:
            email_recieved, email_time = self.email.get_email()
        except:
            email_recieved = False
            email_time = 0
            print("Error recieving email.")

        if (email_recieved):
            self.prev_time_email = time.time()
            self.disabled_time = email_time
            print(self.disabled_time)

        if (time.time() - self.prev_time_email > self.disabled_time):
            self.sprinkler_enabled = True
        else:
            self.sprinkler_enabled = False

        if (email_recieved):
            self.modify_watering(self.sprinkler_enabled)

        if (time.time() - self.prev_time_weather > self.weather.checkIncrement):
            print("Checking weather")
            self.prev_time_weather = time.time()
            try:
                self.weather.check_weather()
                GPIO.output(11, False)  # Turn off flashing red data error light if flashing, routine successful
            except:  # Data unavailable - either connection error, or network error
                GPIO.output(11, True)  # Turn on flashing red data error light
                print("Error contacting DarkSky. Trying again in " + str(self.weather.checkIncrement / 60) + " minute(s)")

            # Now that we know current conditions and forecast, modify watering schedule
            self.modify_watering(self.sprinkler_enabled)

    def modify_watering(self, enabled):
        if (enabled):
            print("\nLast rain from forecast timestamp: " + str(self.weather.lastRain))
            print("Current Time: " + time.asctime(time.localtime(time.time())))
            print("Days since last rain: " + str((time.time() - self.weather.lastRain) / 86400))
            print("Seconds since last rain: " + str(time.time() - self.weather.lastRain))
            print("Days disabled in seconds: " + str(self.weather.daysDisabled * 86400))
            print("Has NOT rained within daysDisabled range: " + str(time.time() - self.weather.lastRain >= self.weather.daysDisabled * 86400))

            if (self.weather.rainForecasted == False and time.time() - self.weather.lastRain >= self.weather.daysDisabled * 86400):
                print("Hasn't rained in a while, and not expected to rain. Watering enabled.")
                GPIO.output(7, True)  # Turn off relay switch, enable watering
                GPIO.output(13, True)  # Turn on green light
                GPIO.output(15, False)  # Turn off red light
            else:
                GPIO.output(7, False)  # Turn on relay switch, disable watering
                GPIO.output(13, False)  # Turn off green light
                GPIO.output(15, True)  # Turn on red light
                if (self.weather.rainForecasted):
                    print("Rain is forecasted, or raining today. Watering Disabled")
                else:
                    print("Rain not in forecast, but it has rained recently. Watering Disabled")
        else:
            print("\n### Watering disabled by email ###\n")
            GPIO.output(7, False)  # Turn on relay switch, disable watering
            GPIO.output(13, False)  # Turn off green light
            GPIO.output(15, True)  # Turn on red light

    def get_program_dir(self):
        '''
        This funtion gets the path of this file.  When run at startup, we need full path to access config file
        To run this file automatically at startup, change permission of this file to execute
        If using wireless for network adapter, make sure wireless settings are configured correctly in wlan config so wifi device is available on startup
        edit /etc/rc.local file 'sudo pico /etc/rc.local'
        add "python /home/pi/working-python/weather-json.py &" before line "exit 0"
        '''
        try:  # If running from command line __file__ path is defined
            return os.path.dirname(os.path.abspath(__file__)) + "/"
        except:  # If __file__ is undefined, we are running from idle ide, which doesn't use this var
            return os.getcwd() + "/"

    def load_config(self):
        '''
        Load values from config file, or create it and get values
        '''
        config = configparser.ConfigParser()
        try:  # Attempt to open existing cfg file
            config.read(self.get_program_dir() + 'sprinkler.cfg')
            print("Config file found, loading previous values...")

            self.api_key = config['DEFAULT']['api_key']
            self.latitude = config['DEFAULT']['latitude']
            self.longitude = config['DEFAULT']['longitude']
            self.precip_threshold = float(config['DEFAULT']['precip_threshold'])
            self.server = config['DEFAULT']['server']
            self.username = config['DEFAULT']['username']
            self.password = config['DEFAULT']['password']
            self.admin_email = config['DEFAULT']['admin_email']
            self.daysDisabled = int(float(config['DEFAULT']['days_disabled']))
            self.checkIncrement = int(float(config['DEFAULT']['check_increment']))

        except:  # Exception: config file does not exist, create new
            print("Config file not found, creating new...")

            self.api_key = input("Enter DarkSky API key: ")
            self.latitude = input("Enter latitude: ")
            self.longitude = input("Enter longitude: ")
            self.precip_threshold = float(input("Enter percipitation threshold: "))
            self.server = input("Enter mail server address: ")
            self.username = input("Enter email address: ")
            self.password = input("Enter email password: ")
            self.admin_email = input("Enter email to accept commands from: ")
            self.daysDisabled = int(input("Enter number of days to disable system prior/after rain (between 1 and 7): "))
            self.checkIncrement = 86400 / int(input("Enter number of times you want to check forecast per 24-hour period (try 24, or once per hour): "))

            config['DEFAULT'] = {
                'api_key': self.api_key,
                'latitude': self.latitude,
                'longitude': self.longitude,
                'precip_threshold': self.precip_threshold,
                'server': self.server,
                'username': self.username,
                'password': self.password,
                'admin_email': self.admin_email,
                'days_disabled': self.daysDisabled,
                'check_increment': self.checkIncrement
            }
            with open('sprinkler.cfg', 'w') as configfile:
                config.write(configfile)


if __name__ == "__main__":
    program = sprinkler()
    while True:
        program.main()
