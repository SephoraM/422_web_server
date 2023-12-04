from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from collections import deque
import atexit
import random
import os

# ----------------Global variables-------------------

# the app
smart_road_app = Flask(__name__)

weather_options = ['sunshine', 'rain', 'snow', 'blizzard'] # to simulate weather data
time_of_day_options = ['day', 'night'] # to simulate time of day
congestion_options = ['none', 'light', 'medium', 'heavy']

near_collisions = 0 # near collision reports

current_car_count = 0 # will store 30 seconds worth of car counts
logs = deque(maxlen=30) # will be displayed in browser

# this can hold a maximum of 17 elements and will be upated every 10 seconds
# meaning that it will store the previous 2.9 minutes of car counts
car_counts = deque(maxlen=17)

# the values returned by the get requests. Represented as a number
current_road_condition = 1
congestion = 1
# ------------------Helper functions--------------------

# when a new near collision is posted
def update_near_collisions(count):
    global near_collisions
    near_collisions += count
    logs.append(f"Total near collisions reported: {near_collisions}.")

# when a new count is posted
def update_count(count):
    global current_car_count
    current_car_count += count

# scheduled task
def update_car_counts():
    global current_car_count
    logs.append(f"Car count within past 3 minutes: {sum(car_counts) + current_car_count}.")
    car_counts.append(current_car_count) # first in is replaced if length greater than 9
    current_car_count = 0 # reset current car count

# congestion is relevant for the past 3 minutes
def update_congestion():
    global congestion
    recent_cars = sum(car_counts) + current_car_count
    if recent_cars > 10:
        congestion = 4
    elif recent_cars > 5:
        congestion = 3
    elif recent_cars > 0:
        congestion = 2
    else:
        congestion = 1  

# to select the traffic sequence and message
def update_road_condition():
    global current_road_condition
    current_weather = random.choice(weather_options) # select a random weather option
    current_time_of_day = random.choice(time_of_day_options) # select a random time of day
    if current_weather == 'blizzard':
        current_road_condition = 6 
    elif current_weather == 'snow':
        current_road_condition = 5
    elif current_weather == 'rain':
        if congestion > 2:
            current_road_condition = 4
        else:
            current_road_condition = 3
    elif current_time_of_day == 'day': # by default, sunny
        current_road_condition = 2
    else:
        current_road_condition = 1 # night
    logs.append(f"Current road conditions: weather: {current_weather}, time of day {current_time_of_day}, congestion {congestion_options[congestion-1]}.")
    

#----------------------------Routes-----------------------

# index page so we can see logs
@smart_road_app.route('/')
def index():
    return render_template('index.html')

# route for near collisions
@smart_road_app.route('/post_near_collisions', methods=['POST'])
def post_near_collisions():
    body = request.json
    if body.get('collisions') is not None:
        update_near_collisions(body.get('collisions')) # add to near collision count
    return jsonify({"message": "Success"})

# route for car counts
@smart_road_app.route('/post_count', methods=['POST'])
def post_count():
    body = request.json
    if body.get('value') is not None:
        update_count(body.get('value')) # add to car count
    return jsonify({"message": "Success"})

# for congestion
@smart_road_app.route('/get_congestion', methods=['GET'])
def get_device_updates():
    return jsonify({"congestion": congestion})

# for the road conditions
@smart_road_app.route('/get_road_conditions', methods=['GET'])
def get_road_conditions():
    return jsonify({"road_condition": current_road_condition})

# for both the road conditions and congestion
@smart_road_app.route('/get_all_conditions', methods=['GET'])
def get_all_conditions():
    return jsonify({"road_condition": f"{current_road_condition},{congestion}"})

# for displaying the current road conditions
@smart_road_app.route('/get_road_condition_logs')
def get_road_condition_logs():
    return jsonify(list(logs))

#-------------------------Scheduler------------------------------

# background scheduler for scheduled tasks
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_car_counts, trigger="interval", seconds=10)
scheduler.add_job(func=update_road_condition, trigger="interval", seconds=30)
scheduler.add_job(func=update_congestion, trigger="interval", seconds=5)
scheduler.start()

# make sure the scheduler is shutdown properly
@smart_road_app.before_first_request
def scheduler_shutdown():
    atexit.register(lambda: scheduler.shutdown())

# ----- main program

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) 
    smart_road_app.run(host='0.0.0.0', port=port)

