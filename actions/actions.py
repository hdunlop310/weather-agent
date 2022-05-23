# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import time
import math
from datetime import timedelta
import datetime
from dateutil.parser import parse
import json
import random
import socket
from ip2geotools.databases.noncommercial import DbIpCity
from geopy.geocoders import Nominatim

humidity = []
wind = []
wind_direction = []
cloud_percent = []
pressure = []

def get_activity_information(lat,lon,category,key):
    response = (requests.get(
        f"https://api.geoapify.com/v2/places?categories={category}&filter=circle:{lon},{lat},5000&bias=proximity:{lon},{lat}&lang=en&limit=20&apiKey={key}"))

    response = response.json()
    choice = random.randint(0, 20)
    try:
        name = response['features'][choice]['properties']['name']
        address = response['features'][choice]['properties']['street'], response['features'][choice]['properties']['postcode']
        info = name, address
    except:
        info = None
    return info

def get_user_city():
    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    location = requests.get(f"http://api.hostip.info/get_html.php?ip={IPAddr}").text.split()
    return location[5]


def get_timestamp(date):
    return time.mktime(datetime.datetime.strptime(date, "%d/%m/%Y").timetuple())


def get_weather_warnings(lat, lon, key):
    response = (requests.get(f"https://api.weatherbit.io/v2.0/alerts?lat={lat}&lon={lon}&key={key}")).json()
    try:
        severity = response['alerts'][0]['severity']
        warning_for = response['alerts'][0]['title']
        description = response['alerts'][0]['description']
        info = (severity, warning_for, description)
    except:
        info = None
    return info


def get_api_key_geoapi():
    with open("api_key_geoapi.txt", 'r') as f:
        return f.read().strip()


def get_api_key_weatherbit():
    with open("api_key_weatherbit.txt", 'r') as f:
        return f.read().strip()


def get_api_key_openweather():
    with open("api_key.txt", 'r') as f:
        return f.read().strip()


def get_lat_lon(city, key):
    response = (requests.get(
        f"http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={key}")).json()
    lat = response[0]['lat']
    lon = response[0]['lon']
    return lat, lon


def get_weather_for_specific_time_historical(lat, lon, key, time):
    timestamp = math.trunc(get_timestamp(time))
    response = (requests.get(
        f"http://history.openweathermap.org/data/2.5/history/city?lat={lat}&lon={lon}&type=hour&start={timestamp}&end={timestamp}&appid={key}")).json()

    global humidity, wind, wind_direction, cloud_percent, pressure
    humidity = response['list'][0]['main']['humidity']
    wind = response['list'][0]['wind']['speed']
    wind_direction = response['list'][0]['wind']['deg']
    cloud_percent = response['list'][0]['clouds']['all']
    pressure = response['list'][0]['main']['pressure']
    general_description = response['list'][0]['weather'][0]['description']
    feels_like = response['list'][0]['main']['feels_like']
    average_temp = response['list'][0]['main']['temp']
    try:
        rain_chance = response['list'][0]['pop'] * 100
    except:
        rain_chance = None
    return general_description, average_temp, rain_chance, feels_like


def get_weather_for_specific_time_future(lat, lon, key, days):
    days = abs(days)
    response = (requests.get(
        f"http://api.openweathermap.org/data/2.5/forecast/daily?lat={lat}&lon={lon}&cnt={days + 1}&appid={key}")).json()
    print(response)
    global humidity, wind, wind_direction, cloud_percent, pressure
    humidity = response['list'][days - 1]['humidity']
    wind = response['list'][days - 1]['speed']
    morning = response['list'][days - 1]['temp']['morn']
    day = response['list'][days - 1]['temp']['day']
    night = response['list'][days - 1]['temp']['night']
    evening = response['list'][days - 1]['temp']['eve']
    average_temp = get_avg_temp(morning, day, night, evening)
    rain_chance = response['list'][days - 1]['pop'] * 100
    general_description = response['list'][days - 1]['weather'][0]['description']
    feels_like = response['list'][0]['feels_like']['day']
    wind_direction = response['list'][0]['deg']
    cloud_percent = response['list'][0]['clouds']
    pressure = response['list'][0]['pressure']

    return general_description, average_temp, rain_chance, feels_like


def get_avg_temp(morning, day, night, evening):
    return sum([morning, day, night, evening]) / 4


def try_date_format(date, format):
    try:
        result = bool(datetime.datetime.strptime(date, format))
    except ValueError:
        result = False
    return result


def extract_day_from_slot(date_slot, days):
    for day in days:
        if day in date_slot.lower():
            return day
    return None


def get_next_weeks_date(date_slot):
    days_dict = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    days = days_dict.keys()
    desired_day = extract_day_from_slot(date_slot, days)
    if desired_day is not None:
        today = datetime.datetime.strftime(datetime.datetime.now(), '%d/%b/%Y')
        dt = datetime.datetime.strptime(today, '%d/%b/%Y')
        week_beginning = dt - timedelta(days=dt.weekday())
        next_week_beginning = week_beginning + timedelta(days=7)
        days_to_add = days_dict[desired_day]
        correct_date = next_week_beginning + timedelta(days=days_to_add)
        return correct_date
    else:
        return "error: day not found"


def remove_suffix_and_redundant_words(date_slot):
    if "the" in date_slot:
        date_slot = date_slot.replace("the", "")

    date_suffixes = ["st", "th", "rd"]

    for suffix in date_suffixes:
        date_slot = date_slot.replace(suffix, "")

    date_slot = date_slot.replace("of", "")
    return date_slot


def date_parser(date_slot):
    if date_slot is None or date_slot == "today":
        return datetime.datetime.now()
    else:
        if "next" in date_slot:
            return get_next_weeks_date(date_slot)
        else:
            date_slot = remove_suffix_and_redundant_words(date_slot)
            if is_date(date_slot):
                if try_date_format(date_slot, "%d   %B %Y"):
                    return datetime.datetime.strptime(date_slot, "%d   %B %Y")
                elif try_date_format(date_slot, "%d  %B"):
                    date_slot = date_slot + datetime.datetime.now().year
                    return datetime.datetime.strptime(date_slot, "%d  %B %Y")
                elif try_date_format(date_slot, "%B  %d"):
                    date_slot = date_slot + " " + str(datetime.datetime.now().year)
                    return datetime.datetime.strptime(date_slot, "%B  %d %Y")
                elif try_date_format(date_slot, "%d"):
                    date_slot = date_slot + " " + str(datetime.datetime.now().month) + " " + str(
                        datetime.datetime.now().year)
                    return datetime.datetime.strptime(date_slot, "%d %m %Y")
                else:
                    return None
            elif date_slot == "tomorrow":
                return datetime.date.today() + timedelta(days=1)
            elif date_slot == "day after tomorrow":
                return datetime.date.today() + timedelta(days=2)
            else:
                return "date could not be found"


def is_date(string, fuzzy=False):
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def check_how_long_ago_date_was_from_current_date(date_time):
    today = datetime.datetime.today()
    return (today - date_time).days


def format_date(date):
    return date.strftime("%d/%m/%Y")


class GetWeather(Action):

    def name(self) -> Text:
        return "weather_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        key = get_api_key_openweather()
        city = tracker.get_slot('city')
        date = tracker.get_slot('date')

        date = date_parser(date)
        if check_how_long_ago_date_was_from_current_date(date) > 0:
            date = format_date(date)
            lat, lon = get_lat_lon(city, key)
            general_description, average_temp, rain_chance, feels_like = get_weather_for_specific_time_historical(lat, lon, key,
                                                                                                      date)
        elif check_how_long_ago_date_was_from_current_date(date) <= 0:
            days = check_how_long_ago_date_was_from_current_date(date)
            date = format_date(date)
            lat, lon = get_lat_lon(city, key)
            general_description, average_temp, rain_chance, feels_like = get_weather_for_specific_time_future(lat, lon, key, days)

        message = f"The weather in {city.title()} on {date} is forecasted to be {general_description}. There is {rain_chance}% chance of rain and the average temperature is forecasted to be {math.trunc(average_temp)} degrees Kelvin. The 'feels like' temperature is {feels_like}. Is there anything else I can help you with?"

        dispatcher.utter_message(text=message)

        return []


class GetDetails(Action):

    def name(self) -> Text:
        return "request_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        requests = tracker.get_slot('request')
        message = ""
        for request in requests:
            if request == "humid" or request == "humidity":
                message += f"The humidity is forecasted to be {humidity}% "
            if request == "wind" or request == "windy":
                message += f"The wind speed is forecasted to be {wind}mph."
            if request == "wind direction" or request == "direction":
                message += f"The wind direction is forecasted to be at {wind_direction} degrees."
            if request == "pressure":
                message += f"The pressure is forecasted to be {pressure} hPa."
            if request == "cloudy" or request == "clouds":
                message += f"The amount of clouds is forecasted to be {cloud_percent}%"

        dispatcher.utter_message(message)
        return []


class GetWarnings(Action):

    def name(self) -> Text:
        return "warning_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        open_weather_key = get_api_key_openweather()
        weather_bit_key = get_api_key_weatherbit()
        city = tracker.get_slot('city')
        city_default = get_user_city()
        message = ""
        if city is None:
            lat, lon = get_lat_lon(city_default, open_weather_key)
        else:
            lat, lon = get_lat_lon(city, open_weather_key)
        info = get_weather_warnings(lat, lon, weather_bit_key)
        if info is None:
            message += "There are no warnings in the area."
        else:
            severity, warning_for, description = info
            description = description.split()
            description.pop(0)
            description = " ".join(description)
            message += f"There are {severity.lower()} warnings for {warning_for} in the area. The description provided is as " \
                       f"follows: {description}. "
        dispatcher.utter_message(message)
        return []


class GetActivity(Action):

    def name(self) -> Text:
        return "activity_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        open_weather_key = get_api_key_openweather()
        geoapi_key = get_api_key_geoapi()
        city = tracker.get_slot('city')
        activity = tracker.get_slot('activity')
        city_default = get_user_city()
        message = ""
        print(city)
        if city is None:
            lat, lon = get_lat_lon(city_default, open_weather_key)
        else:
            lat, lon = get_lat_lon(city, open_weather_key)

        allowed_categories = {
            "park":"national_park",
            "museum": "entertainment.museum",
            "cinema": "entertainment.cinema",
            "zoo":"entertainment.zoo",
            "gallery":"entertainment.culture.gallery",
            "tourist attraction": "tourism.attraction",
            "restaurant": "catering.restaurant",
            "pub": "catering.pub"
            }

        for category in allowed_categories.keys():
            if category in activity:
                info = get_activity_information(lat,lon,allowed_categories[category],geoapi_key)
                if info is not None:
                    name, address = info
                    street, postcode = address
                    message = f"A good {category} in {city} is {name} in {street} street, {postcode}"
                    break
                else:
                    message += f"No {activity} found in the area, sorry."

        if message == "":
            message = "Unkown activity, sorry. You can search for parks, museums, cinemas, zoos, galleries, tourist attractions, restaurants and pubs."

        dispatcher.utter_message(message)
        return []
