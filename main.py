import duckdb,os,time,pytz
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime,timedelta


# Backend Loading

# Load Json
workout_json_file_path = "workout_data.json"
workout_counts_json_file_path = "workout_counts.json"

if os.path.exists(workout_json_file_path):
  workout_df = pd.read_json(workout_json_file_path)
  workout_counts_df = pd.read_json(workout_counts_json_file_path, orient='index')
  workout_counts_df.reset_index(inplace=True)
  workout_counts_df.columns = ['Type', 'Count']
  workout_df['created_at'] = workout_df['created_at'].dt.tz_localize('UTC')
  workout_df['created_at'] = workout_df['created_at'].dt.tz_convert('US/Eastern')
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


# Frontend
st.header("tatertotss's Metrics Dashboard")
padding_fivepx()


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
        workout_counts_df_filtered = workout_counts_df[workout_counts_df['Count'] > 2]
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
        instructors_more_than_five_classes = filtered_workout_df['instructor'].value_counts()[filtered_workout_df['instructor'].value_counts() > 5].index
        filtered_workout_df = filtered_workout_df[filtered_workout_df['instructor'].isin(instructors_more_than_five_classes)]
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

    #Github-like year calendar
    past_year_df = past_year_df.copy() 
    past_year_df['date'] = past_year_df['created_at'].dt.date.astype(str)

    # Calculate the total distance covered per day
    daily_total_distance = past_year_df.groupby('date')['distance'].sum().reset_index()
    daily_total_distance['date'] = pd.to_datetime(daily_total_distance['date'])

    ###OFFSET:
    # daily_total_distance['date'] += pd.Timedelta(days=1) #adding an offset for display

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

##test
# st.write(daily_total_distance)
# print(daily_total_distance.dtypes)





