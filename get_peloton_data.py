import json, os
from peloton_client import peloton_client
from pprint import pprint


#Restructuring list of dicts to single dict
def extract_data(input_data):
    output_dict = {}
    for x in input_data:
        output_dict[x.get('slug')] = x.get('value')
    return output_dict

#Getting & structuring the workout data
def get_workout_data(workouts):
    workout_data = []
    for workout in workouts:
        output_dict = {}
        workout_metrics = client.fetch_workout_metrics(workout.get('id'))
        workout_core_stats = extract_data(workout_metrics.get('summaries'))
        workout_core_averages = extract_data(workout_metrics.get('average_summaries'))

        #Code for getting HR Zones
        effort_zones_data = workout.get('effort_zones')
        if not effort_zones_data:
            effort_zones_data = {}
            # Handle non-serializable types in effort_zones_data
            for zone in ['heart_rate_z1_duration', 'heart_rate_z2_duration', 'heart_rate_z3_duration', 'heart_rate_z4_duration', 'heart_rate_z5_duration']:
                output_dict[zone] = json.dumps(effort_zones_data.get('heart_rate_zone_durations', {}).get(zone, {}))
        # print(type(effort_zones_data), effort_zones_data)
        heart_rate_zone_durations = effort_zones_data.get('heart_rate_zone_durations', {})


        try:
            output_dict = {
                'distance': workout_core_stats.get('distance'),
                'output': workout_core_stats.get('total_output'),
                'cals': workout_core_stats.get('calories'),
                'speed': workout_core_averages.get('avg_speed'),
                'duration': workout.get('ride').get('duration') / 60,
                'title': workout.get('ride').get('title'),
                'created_at': workout.get('created_at'),
                'discipline': workout.get('fitness_discipline'),
                'instructor': workout.get('ride').get('instructor', {}).get('name') if workout.get('ride') and workout.get('ride').get('instructor') else None,
                'heart rate': workout_core_stats.get('heart_rate'),
                'heart_rate_z1_duration': heart_rate_zone_durations.get('heart_rate_z1_duration', 0),
                'heart_rate_z2_duration': heart_rate_zone_durations.get('heart_rate_z2_duration', 0),
                'heart_rate_z3_duration': heart_rate_zone_durations.get('heart_rate_z3_duration', 0),
                'heart_rate_z4_duration': heart_rate_zone_durations.get('heart_rate_z4_duration', 0),
                'heart_rate_z5_duration': heart_rate_zone_durations.get('heart_rate_z5_duration', 0)
            }
            workout_data.append(output_dict)
            print(workout.get('ride').get('title'))
        except Exception as e:
            print(f"Error parsing workout: {e}")
            print(f"Output Dict: \n{e}")
    return workout_data


#Get workout count info
def get_user_overview(overview):
    workout_counts = overview.get('workout_counts', {}).get('workouts', [])
    workout_counts_dict = {}

    for workout in workout_counts:
        workout_name = workout.get('name', '')
        count = workout.get('count', 0)
        workout_counts_dict[workout_name] = count

    return workout_counts_dict


workout_data_file_path = "workout_data.json"

try:
    client = peloton_client.PelotonClient(username="", password="")
    
    # Check if workout_data.json exists
    if not os.path.isfile(workout_data_file_path):
        # Fetch all workout data if workout_data.json doesn't exist
        workouts = client.fetch_workouts(fetch_all=True)
    else:
        # Otherwise, fetch limited workout data
        workouts = client.fetch_workouts()

    workouts_data = get_workout_data(workouts)

    # Grab workout counts
    overview = client.fetch_user_overview()
    overview_data = get_user_overview(overview)

    # Write workout counts to json
    workout_counts_file_path = "workout_counts.json"
    with open(workout_counts_file_path, "w") as json_file:
        json.dump(overview_data, json_file)

    # If workout_data.json doesn't exist, write all workout data to the file
    if not os.path.isfile(workout_data_file_path):
        with open(workout_data_file_path, "w") as json_file:
            json.dump(workouts_data, json_file)
    else:
        # Read existing workout_data JSON 
        with open('workout_data.json', 'r') as json_file:
            existing_data = json.load(json_file)
            
        #Get timestamp of most recent workout
        latest_timestamp = max(entry['created_at'] for entry in existing_data)
        print(latest_timestamp)

        # Retrieve new workout data & update workout_data json
        new_workout_data = [data for data in workouts_data if data['created_at'] > latest_timestamp]

        if new_workout_data:
            existing_data.extend(new_workout_data)
            existing_data.sort(key=lambda x: x['created_at'])
            latest_timestamp = max(entry['created_at'] for entry in existing_data)

            # Save the updated JSON back to the file
            with open('workout_data.json', 'w') as json_file:
                json.dump(existing_data, json_file, indent=4)

            print("New data appended if any.")
        else:
            print("No new data")

except Exception as e:
    print(f"error: {e}")





