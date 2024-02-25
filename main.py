import duckdb,os,time,pytz,json,io
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from pprint import pprint
from datetime import datetime,timedelta
from google.cloud import storage
from peloton_client import peloton_client

################# Backend Loading #################

#Load GCS Jsons
storage_client = storage.Client()
json_bucket = "streamlit-peloton-bucket"
bucket = storage_client.bucket(json_bucket)

# Define files in GCS
workout_json_blob = bucket.blob("workout_data.json")
workout_counts_json_blob = bucket.blob("workout_counts.json")

# Read JSON files from GCS
if workout_json_blob.exists() and workout_counts_json_blob.exists():

    #Handling workout data
    workout_json_data = json.loads(workout_json_blob.download_as_string())
    workout_df = pd.DataFrame(workout_json_data)
    workout_df['created_at'] = pd.to_datetime(workout_df['created_at'], unit='s')
    workout_df['created_at'] = workout_df['created_at'].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
    
    #Handling workout counts
    workout_counts_json_data = json.loads(workout_counts_json_blob.download_as_string())
    json_buffer = io.BytesIO(workout_counts_json_blob.download_as_string())
    workout_counts_df = pd.read_json(json_buffer, orient='index')
    workout_counts_df.reset_index(inplace=True)
    workout_counts_df.columns = ['Type', 'Count']

    # print(workout_df.dtypes)
    # print(workout_df.info())
else:
    st.write("Lol where's the jsons")


def padding_fivepx():
    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

#time shenanigans
timezone = pytz.timezone('US/Eastern')
current_date = datetime.now(timezone).date()
midnight_datetime = timezone.localize(datetime.combine(current_date, datetime.min.time()))

past_year_date = current_date - timedelta(days=365)
past_year_datetime = timezone.localize(datetime.combine(past_year_date, datetime.min.time()))
past_year_df = workout_df[workout_df['created_at'] > past_year_datetime]

################get peloton api data######################
username = os.getenv("PELOTON_USERNAME")
password = os.getenv("PELOTON_PASSWORD")
if username is None or password is None:
    raise ValueError("Peloton username or password is not provided. Please set PELOTON_USERNAME and PELOTON_PASSWORD environment variables.")

client = peloton_client.PelotonClient(username=username, password=password)

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

def get_peloton_data():
    workout_data_file_path = "workout_data.json"
    #defined above:
    # workout_json_blob = bucket.blob("workout_data.json")
    # workout_counts_json_blob = bucket.blob("workout_counts.json")

    try:
        print("getting latest data")
        workouts = client.fetch_workouts()
        workouts_data = get_workout_data(workouts)

        existing_data = json.loads(workout_json_blob.download_as_string())
        latest_timestamp = max(entry['created_at'] for entry in existing_data)
        new_workout_data = [data for data in workouts_data if data['created_at'] > latest_timestamp]

        if new_workout_data:
            # Update existing workout data
            existing_data.extend(new_workout_data)
            existing_data.sort(key=lambda x: x['created_at'])
            latest_timestamp = max(entry['created_at'] for entry in existing_data)

            # Upload the updated JSON back to the blob
            workout_json_blob.upload_from_string(json.dumps(existing_data), content_type="application/json")

            print("New data appended")
        else:
            print("No new data")


        # Grab workout counts
        overview = client.fetch_user_overview()
        overview_data = get_user_overview(overview)
        overview_json_string = json.dumps(overview_data)
        workout_counts_json_blob.upload_from_string(overview_json_string, content_type="application/json")


    except Exception as e:
        print(f"error: {e}")


################# Frontend #################
st.header("tatertotss's Metrics Dashboard")
padding_fivepx()

#Get latest data button
get_data_button = st.button("Get Latest Data")
if get_data_button:
    # Display a loading indicator
    with st.spinner("Fetching data..."):
        # Call the get_peloton_data function
        get_peloton_data()
    
    # Display the fetched data
    st.write("Data updated")

# st.dataframe(workout_df)

# Container 1
with st.container():
    col1, col2 = st.columns(2)

    # Column 1
    with col1:

        # Todays Metrics
        st.subheader("Today's Metrics")
        padding_fivepx()

        today_df = workout_df[workout_df['created_at'] > midnight_datetime]

        if today_df.empty:
            st.write("🦗")
            st.write("No workouts yet...")
            st.write("Go generate some data, tatertotss! 😉")
        else:
            # Display workout titles and instructors
            st.write("**Workouts Taken:**")
            for index, row in today_df.iterrows():
                st.write(f"- {row['title']}, {row['instructor']}")

            # Display total calories burned
            total_cals_burned = today_df['cals'].sum()
            st.write("🔥 **Total Calories Burned:**", str(total_cals_burned))
            
            # Display total distance covered
            if today_df['distance'].isnull().all():
              total_distance_covered = "N/A"
            else: 
              total_distance_covered = today_df['distance'].sum()
            st.write("⚡ **Total Distance Covered:**", str(total_distance_covered))
            
            # Display total kilojoules jouled
            if today_df['output'].isnull().all():
                total_kilojoules = "N/A"
            else:
                # Calculate the sum of 'output' column
                total_kilojoules = today_df['output'].sum()
            st.write("🚀 **Total Kilojoules Jouled:**", str(total_kilojoules))


    # Column 2
    with col2:

        # All classes taken by discipline
        st.subheader("All classes taken by discipline")
        workout_counts_df_filtered = workout_counts_df[workout_counts_df['Count'] > 3]
        source = pd.DataFrame({
            'classes taken': workout_counts_df_filtered['Count'],
            'workout type': workout_counts_df_filtered['Type']
        })
        chart = alt.Chart(source).mark_arc(innerRadius=50).encode(
            theta="classes taken",
            color=alt.Color("workout type:N", sort=alt.EncodingSortField(field="classes taken", order='descending')),
            tooltip=["workout type:N", "classes taken:Q"],
        ).properties(
            width=300,
            height=300,
            # title='Number of classes taken by discipline'
        )
        # st.write("## Altair Chart")
        st.altair_chart(chart, use_container_width=True)



#Container 2
with st.container():
    col3, col4 = st.columns(2)

    #Col 3
    with col3:


        # Create and display first chart, col3
        workout_df['month'] = workout_df['created_at'].dt.month
        workout_df['year'] = workout_df['created_at'].dt.year
        monthly_distance = workout_df.groupby(['year', 'month'])['distance'].sum().reset_index()
        st.subheader("Distance by Month and Year")

        chart = alt.Chart(monthly_distance).mark_line().encode(
            x='month:O',  # 'O' for ordinal scale since it represents months
            y='distance:Q',  # 'Q' for quantitative scale for distance
            color='year:N',  # 'N' for nominal scale for years
            tooltip=['year:N', 'month:O', 'distance:Q']  # Add tooltip for year, month, and distance
        ).properties(
            width=300,
            height=300,
            # title='Distance by Month and Year'  # Set the title of the chart
        )
        st.altair_chart(chart, use_container_width=True)



    #Col 4
    with col4:


        # Create and display first chart, col4
        st.subheader("Workout Counts by Instructor")
        filtered_workout_df = workout_df[~workout_df['instructor'].isin(['JUST WALK', 'JUST RIDE', 'JUST CARDIO', 'JUST LIFT'])]
        instructors_more_than_ten_classes = filtered_workout_df['instructor'].value_counts()[filtered_workout_df['instructor'].value_counts() > 10].index
        filtered_workout_df = filtered_workout_df[filtered_workout_df['instructor'].isin(instructors_more_than_ten_classes)]
        instructor_counts = filtered_workout_df['instructor'].value_counts().reset_index()
        instructor_counts.columns = ['instructor', 'count']

        chart = alt.Chart(instructor_counts).mark_bar().encode(
            y=alt.Y('instructor:N', sort='-x'),
            x='count:Q',
            tooltip=['instructor:N', 'count:Q'],
            color=alt.Color('instructor:N', legend=None)
        ).properties(
            # title='Workout Counts by Instructor',
            width=300,
            height=300
        )
        st.altair_chart(chart, use_container_width=True)


#Container 3
with st.container():

    #Github-like year calendar:
    #past_year_df created in backend loading section towards the top 
    past_year_df = past_year_df.copy() 
    past_year_df['date'] = past_year_df['created_at'].dt.date.astype(str)

    # Calculate the total distance covered per day
    daily_total_distance = past_year_df.groupby('date')['distance'].sum().reset_index()
    daily_total_distance['date'] = pd.to_datetime(daily_total_distance['date'])

    ###OFFSET DATES CODE:
    daily_total_distance['date'] += pd.Timedelta(days=1) #add an offset for display

    # Create the Altair chart with tooltips
    chart = alt.Chart(daily_total_distance, title="Daily Total Distance Covered").mark_rect().encode(
        alt.X("date(date):O", title="Day"),
        alt.Y("month(date):O", title="Month"),
        alt.Color("distance:Q", title="Total Distance", scale=alt.Scale(scheme='viridis')),
        tooltip=[
            alt.Tooltip("date(date)", title="Date"),
            alt.Tooltip("month(date):O", title="Month"),
            alt.Tooltip("distance:Q", title="Total Distance"),
        ],
    ).configure_view(
        step=13,
        strokeWidth=0
    ).configure_axis(
        domain=False
    )
    st.altair_chart(chart, use_container_width=True)

##test area
# st.write(daily_total_distance)
# print(daily_total_distance.dtypes)





