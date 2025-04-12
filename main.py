import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time


# display last updated
def time_difference_to_string(time_diff):
    seconds = time_diff.total_seconds()

    if seconds < 60:
        return "few seconds ago"
    elif seconds < 2 * 60:
        return "less than 2 minutes ago"
    elif seconds < 3 * 60:
        return "less than 3 minutes ago"
    elif seconds < 6 * 60:
        return "less than 5 minutes ago"
    elif seconds < 15 * 60:
        return "less than 15 minutes ago"
    elif (seconds < 60 * 60) and (seconds > 15 * 60):
        return "more than 15 minutes ago"
    elif (seconds > 60 * 60) and (seconds < 24 * 60 * 60):
        return "more than an an hour ago"
    elif seconds > 24 * 60 * 60:
        days = time_diff.days
        return f"{days} days ago"
    else:
        return "several day ago" 


# retrieving parks
def getParkData():
    API_parks = "https://queue-times.com/parks.json"

    response = requests.get(API_parks)
    if response.status_code == 200:

        park_names = []

        for id in response.json():
            for park in id["parks"]:
                park_names.append(park)
        return park_names

    else: 
        return [{      
        "id": 0,
        "name": "Currently no parks available",
        "country": "n/a",
        "continent": "Europe",
        "latitude": "n/a",
        "longitude": "n/a",
        "timezone": "n/a"
      }]


#retrieving waiting time for selected park
def getWaitingTimesData(id):
    API_wait_times = f"https://queue-times.com/parks/{id}/queue_times.json"

    response = requests.get(API_wait_times)
    if response.status_code == 200:

        data = response.json()
        all_rides = []

        for land in data["lands"]:
            for ride in land["rides"]:
                ride["Park area"] = land["name"]
                all_rides.append(ride)

        for ride in data["rides"]:
            ride["Park area"] = "n/a"
            all_rides.append(ride)
        return all_rides

    else: 
        return [{
            "id": "0", 
            "name": "Currently no attractions available",
            "is_open": False, 
            "wait_time": 0, 
            "last_updated": "2023-04-12T07:56:54.000Z", 
            "Park area": "n/a"
        }]
    

# Button state 
if "hide" not in st.session_state:
    st.session_state["hide"]=False

def changeState():
    st.session_state["hide"]=True



# Creating dataframe of parks
df_pn = pd.DataFrame(getParkData())
df_pn = df_pn.rename(columns={"name": "Name", "country": "Country", "continent": "Continent"})
df_pn = df_pn[df_pn["Continent"] == "Europe"]
df_pn["country_and_name"] = df_pn["Country"] + " - " + df_pn["Name"]
df_pn = df_pn.sort_values("country_and_name")



# header
st.markdown("<h1 style='text-align: center;'>Waiting times in European amusement parks</h1>", unsafe_allow_html=True)


# Layout
# Display park selection
selected_park = st.selectbox("Select your park:", df_pn["country_and_name"], index=24)
selected_park_id = df_pn[df_pn["country_and_name"] == selected_park]["id"].values[0]

print(selected_park_id)


# Show only open attractions



only_open_rides = st.checkbox("Show only open attractions", on_change=changeState)


col1, col2 = st.columns(2)
# Refresh button with spinner for user-feedback. No more action needed as by default streamlit rerenders the whole app
with col1:
    if st.button("Refresh waiting times"):
        with st.spinner("Retrieving latest data..."):
            time.sleep(1.5)
with col2:
    st.markdown("<div style='text-align:right'> <a href='https://queue-times.com/' >Powered by Queue-Times.com</a> </div>", unsafe_allow_html=True)


# Create dataframe for waiting times 
df_wt = pd.DataFrame(getWaitingTimesData(selected_park_id))

# Data check and modifying dataframe of waiting times
if len(df_wt.columns) < 1:
    st.write("At this time, no data is available.")

else:
    df_wt["last updated check"] = pd.to_datetime(df_wt["last_updated"], utc=True).dt.tz_convert('Europe/Berlin')#.dt.strftime('%Y-%m-%d %H:%M:%S')
    #df_wt["last_fetched"] = pd.Timestamp.now()
    df_wt["Last updated"] = pd.to_datetime('now').tz_localize('Europe/Berlin') - pd.to_datetime(df_wt["last_updated"], utc=True).dt.tz_convert('Europe/Berlin')#.dt.strftime('%Y-%m-%d %H:%M:%S')
    df_wt["Last data update by park"] = df_wt["Last updated"].apply(time_difference_to_string)
    
    df_wt = (df_wt
            .rename(columns={"name": "Attraction name", "is_open": "Reported as open?", "wait_time": "Waiting time (min)"}).drop(columns=["id"])
            #.set_index("Attraction name")
            .sort_values(["Waiting time (min)", "Reported as open?", "Attraction name"], ascending=[False, False, True])
            [["Attraction name", "Waiting time (min)", "Reported as open?", "Park area", "Last data update by park"]]
    )

    
    if only_open_rides == True:
        st.dataframe(df_wt[df_wt["Reported as open?"] == st.session_state["hide"]], hide_index=True, use_container_width=True)
    else:
        st.dataframe(df_wt, hide_index=True, use_container_width=True)


    # Creating a bit padding
    st.markdown("<br>", unsafe_allow_html=True) 

    # Sort the DataFrame
    df_sorted = df_wt[df_wt["Reported as open?"] == True].sort_values("Waiting time (min)", ascending=True)

    # Dynamically calculate height
    num_attractions = df_sorted.shape[0]
    chart_height = max(400, num_attractions * 30)

    # Create horizontal bar chart
    fig = px.bar(
        df_sorted,
        x="Waiting time (min)",
        y="Attraction name",
        orientation='h',
        title="Attractions by Waiting Time",
        labels={
            "Attraction name": "Attraction Name",
            "Waiting time (min)": "Waiting Time (minutes)"
        }
    )

    # Update layout with custom height
    fig.update_layout(
        height=chart_height,
        yaxis=dict(tickfont=dict(size=12)), 
        yaxis_title=None,
        margin=dict(l=150)  
    )

    # Display in Streamlit
    st.plotly_chart(fig, use_container_width=True)




 
    # Group by park area and sort each group by waiting time
    df_grouped = df_wt[df_wt["Reported as open?"] == True].groupby('Park area').apply(
        lambda x: x.sort_values('Waiting time (min)', ascending=True)
        ).reset_index(drop=True)

    # Dynamically calculate chart height based on number of attractions
    num_attractions = df_grouped.shape[0]
    chart_height = max(500, num_attractions * 30)

    # Create horizontal bar chart
    fig2 = px.bar(
        df_grouped,
        x='Waiting time (min)',
        y='Attraction name',
        color='Park area',
        orientation='h',
        title="Attractions by Waiting Time grouped by Park Area",
        labels={
            'Attraction name': 'Attraction Name',
            'Waiting time (min)': 'Waiting Time (minutes)',
            'Park area': 'Park Area'
        },
        color_discrete_sequence=px.colors.qualitative.Set1
    )

    # Update layout for better readability
    fig2.update_layout(
        height=chart_height,
        yaxis=dict(tickfont=dict(size=12)),
        yaxis_title=None,
        margin=dict(l=160, r=20, t=60, b=40)  # More left margin for long labels
    )

    # Show the chart in Streamlit
    st.plotly_chart(fig2, use_container_width=True)