#!/usr/bin/env python

import os
import time

import requests
import RPi.GPIO as GPIO  # #Import GPIO library


class darkSky():

    def __init__(self, api_key, latitude, longitude, checkIncrement, daysDisabled, precip_threshold):
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.checkIncrement = checkIncrement  # Amount of time between DarkSky forecast requests - integer
        self.daysDisabled = daysDisabled  # Days to disable systems before and after rain - integer
        self.precip_threshold = precip_threshold
        self.lastRain = 0

        # Show values/interval used to check weather
        print("System will be disabled for " + str(self.daysDisabled) + " days prior to and after rain")
        print("System will wait " + str(self.checkIncrement) + " seconds between checks")
        print("     or " + str(float(self.checkIncrement) / 60) + " minute(s) between checks")
        print("     or " + str(float(self.checkIncrement) / 3600) + " hour(s) between checks")

    def check_weather(self):
        response = requests.get('https://api.darksky.net/forecast/' + self.api_key + '/' + self.latitude + ',' + self.longitude + '/?exclude=[currently,minutely,hourly,alerts,flags]').json()

        # Create array to hold forecast values
        dateArray = []

        # Parse XML into array with only pretty date, epoch, and conditions forecast
        for x in response['daily']['data']:
            precipProbability = x['precipProbability']
            precipType = 0
            if (precipProbability <= self.precip_threshold):
                precipType = 'none'
            else:
                precipType = x['precipType']
            dateArray.append([time.asctime(time.localtime(x['time'])).split(' 00')[0], str(x['time']), precipType])

        print("\nCurrent Forecast for current day, plus next 7 is:")
        for x in dateArray:
            print(x[0] + ", " + x[1] + ", " + x[2])

        # Check current day for rain
        print("\n### START Checking if raining TODAY ###")
        if (dateArray[0][2] == 'rain'):  # If is raining today
            self.lastRain = float(dateArray[0][1])  # Save current rain forecast as last rain globally
            print("It will rain today. Storing current epoch as 'last rain': " + str(self.lastRain))
        else:
            print("No rain today")
        print("### END Checking if raining now ###\n")

        # Check if rain is forecast within current range
        print("### START Checking for rain in forecast range ###")
        for x in range(1, self.daysDisabled + 1):
            print("Checking " + dateArray[x][0] + " for rain conditions:")
            if (dateArray[x][2] == 'rain'):
                print("Rain has been forecast. Disabling watering")
                self.rainForecasted = True  # Set global variable outside function scope
                break
            else:
                print("No rain found for current day. Watering may commence")
                self.rainForecasted = False  # Set global variable outside function scope
        print("### END Checking if rain in forecast ###\n")
