import streamlit as st
from googleapiclient.discovery import build
import csv
import re
import os
from functools import reduce
import pickle
import pandas as pd
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

import stripe
import os
# Set your secret key here. Never expose this in your code directly.
stripe.api_key ="sk_test_51PCh8BDIEa0ONJwKp3IWcCsR6jeY1zI0bny9kVJ1saazEJBmyDNn2Y0qIn1gx9YwQXGpQvmnTYnjzyaovQK3S1H100jpGjObtK"

# Product details
product_price = 1000  # price in cents
currency = 'usd'
domain_url = "https://muhammadazeem-eng-yt-dashb-finalized-q8nztq.streamlit.app/"  # Change to your site's domain


# Function to extract video ID from YouTube video link
def extract_video_id(url):
    match = re.match(r'^.*(?:youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=)([^#\&\?]*).*', url)
    if match:
        return match.group(1)
    else:
        st.error("Invalid YouTube video link. Please enter a valid link to cast your vote ")
        return None


# Function to extract and save YouTube video and channel statistics to a CSV file
def save_video_and_channel_stats_to_csv(video_id, api_key):
    youtube = build("youtube", "v3", developerKey=api_key)

    # Make a request to get video details and statistics
    video_request = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    )

    # Execute the request
    video_response = video_request.execute()

    if not video_response['items']:
        st.error("No video found with the given ID. Please check the ID and try again.")
        return None

    video_data = video_response['items'][0]

    # Extract channel ID from video data
    channel_id = video_data['snippet']['channelId']

    # Make a request to get channel details (including subscriber count)
    channel_request = youtube.channels().list(
        part="statistics",
        id=channel_id
    )

    # Execute the channel request
    channel_response = channel_request.execute()

    # Merge video data and channel subscriber count
    subscriber_count = channel_response['items'][0]['statistics']['subscriberCount']
    video_data['statistics']['subscriberCount'] = subscriber_count

    # Define the keys you're interested in
    keys = ['etag', 'id', 'snippet.publishedAt', 'snippet.channelId', 'snippet.title', 'snippet.channelTitle',
            'statistics.viewCount', 'statistics.likeCount', 'statistics.dislikeCount', 'statistics.commentCount',
            'statistics.subscriberCount']

    # Specify the CSV file name
    csv_file = "Video_and_Channel_data.csv"

    # Check if the CSV file already exists
    file_exists = os.path.isfile(csv_file)

    # Prepare the data to be written to CSV
    row = []
    for key in keys:
        # For nested keys, split by '.' and reduce to get the final value
        value = reduce(dict.get, key.split('.'), video_data)
        row.append(value)

    # Writing to CSV
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # If the file doesn't exist, write column names first
        if not file_exists:
            writer.writerow(keys)

        # Writing the data row
        writer.writerow(row)

    return csv_file


# Function to update key statistics based on the latest data in the CSV file
def update_key_statistics():
    csv_file = "Video_and_Channel_data.csv"
    try:
        # Read the last line of the CSV file
        df = pd.read_csv(csv_file)

        # Assuming 'subscriberCount' might not be present in every entry (for backward compatibility)
        subscriber_count = df.get('statistics.subscriberCount', pd.Series([None])).iloc[-1]

        view_count = df['statistics.viewCount'].iloc[-1]
        like_count = df['statistics.likeCount'].iloc[-1]
        dislike_count = df.get('statistics.dislikeCount', pd.Series([0])).iloc[-1]  # Default to 0 if absent
        comment_count = df['statistics.commentCount'].iloc[-1]

        # Extract additional information
        etag = df['etag'].iloc[-1]
        video_id = df['id'].iloc[-1]
        published_at = df['snippet.publishedAt'].iloc[-1]
        channel_id = df['snippet.channelId'].iloc[-1]
        title = df['snippet.title'].iloc[-1]
        channel_title = df['snippet.channelTitle'].iloc[-1]

        # Display statistics including subscriber count and additional information
        st.markdown(f"""
            <div style="text-align: center;">
                <h2>Retrieved Data</h2>
                <ul style="text-align: left; list-style-position: inside;">
                    <li>Views: {view_count}</li>
                    <li>Likes: {like_count}</li>
                    <li>Dislikes: {dislike_count}</li>
                    <li>Comments: {comment_count}</li>
                    <li>Subscribers: {subscriber_count}</li>
                    <li>Etag: {etag}</li>
                    <li>ID: {video_id}</li>
                    <li>Published At: {published_at}</li>
                    <li>Channel ID: {channel_id}</li>
                    <li>Title: {title}</li>
                    <li>Channel Title: {channel_title}</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

        # Plot histogram chart for key statistics
        st.subheader("Histogram Chart for Key Statistics")
        keys = ['statistics.viewCount', 'statistics.likeCount', 'statistics.dislikeCount', 'statistics.commentCount',
                'statistics.subscriberCount']
        key_labels = ['Views', 'Likes', 'Dislikes', 'Comments', 'Subscribers']
        key_values = [df[key].iloc[-1] for key in keys]
        key_stats_df = pd.DataFrame({'Key': key_labels, 'Value': key_values})

        st.bar_chart(key_stats_df.set_index('Key'), use_container_width=True)

        # Add a download button for the CSV file
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=csv_file,
            mime='text/csv',
        )

        # Add a section for Vote Distribution Chart below the download button
        st.subheader("Vote Distribution Chart")
        st.markdown("""
        <ul style="text-align: left; list-style-position: inside;">
            <li>1 for Non-subscriber Positive comment</li>
            <li>1.5 for Subscriber Positive comment</li>
            <li>-1 for Non-subscriber Negative comment</li>
            <li>-1.5 for Subscriber Negative comment</li>
        </ul>
        """, unsafe_allow_html=True)

    except FileNotFoundError:
        st.error("CSV file not found. Please fetch video statistics first.")


def load_and_visualize_votes(filepath="Mughal.csv"):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(filepath)

    # Assuming 'votes' column exists and contains numeric data
    votes_column = 'votes'

    # Filter values in 'votes' into different variables
    votes_1 = df[df[votes_column] == 1]
    votes_1_5 = df[df[votes_column] == 1.5]
    votes_neg_1_5 = df[df[votes_column] == -1.5]
    votes_neg_1 = df[df[votes_column] == -1]

    # Prepare data for the bar chart
    counts = {
        '1.0': len(votes_1),
        '1.5': len(votes_1_5),
        '−1.5': len(votes_neg_1_5),
        '−1.0': len(votes_neg_1)
    }

    # Display the bar chart in Streamlit using the built-in function
    st.bar_chart(data=counts)


# Main function to display the dashboard
def show_dashboard(api_key):
    st.title("")
    video_link = st.text_input("Enter YouTube Video Link:", "")  # Default is empty
    if st.button("Get Video Statistics") and video_link:
        video_id = extract_video_id(video_link)
        if video_id:
            csv_path = save_video_and_channel_stats_to_csv(video_id, api_key)
            if csv_path:
                update_key_statistics()  # Update the key statistics dynamically
    load_and_visualize_votes("Mughal.csv")


# Define the scopes required for accessing YouTube Data API
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']


def get_authenticated_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, or if the token is expired or revoked, let the user log in again
    if not creds or not creds.valid or creds.expired:
        flow = InstalledAppFlow.from_client_secrets_file(
            'creds.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Build the YouTube Data API service
    service = build('youtube', 'v3', credentials=creds)
    return service


def check_subscription(subscriber_channel_id, target_channel_id):
    # Get authenticated YouTube Data API service
    youtube = get_authenticated_service()

    # Call the subscriptions.list method to check if the subscriber_channel_id is subscribed to target_channel_id
    request = youtube.subscriptions().list(
        part="snippet",
        channelId=subscriber_channel_id,
        forChannelId=target_channel_id,
        maxResults=1
    )
    response = request.execute()

    # Check if there are any subscriptions
    subscriptions = response.get('items', [])
    if subscriptions:
        return True
    else:
        return False


def comments_analyser(input_string):
    # Check if the string starts with '*A' or '*B'
    if input_string.startswith('*A'):
        return True
    elif input_string.startswith('*B'):
        return False
    else:
        # Handle cases where the string does not start with either '*A' or '*B'
        return None


def extract_channel_id(channel_link):
    # Split the URL by '/' and extract the part containing the channel ID
    parts = channel_link.split('/')
    channel_id = parts[-1]  # The channel ID is the last part of the URL
    return channel_id


# Function to save video link and text input to CSV
def save_to_csv(video_link, text, vote):
    data = {'Video Link': [video_link], 'Text': [text], 'Votes': [vote]}
    df = pd.DataFrame(data)
    csv_path = "Mughal.csv"

    # Check if CSV file exists
    if not os.path.exists(csv_path):
        df.to_csv(csv_path, index=False)
    else:
        df.to_csv(csv_path, mode='a', header=False, index=False)

    return csv_path


def tab2():
    # User Guide for Vote section
    st.subheader("User Guide for Vote")
    st.markdown("""
    <ul style="text-align: left; list-style-position: inside;">
        <li>PASTE VIDEO'S LINK</li>
        <li>Watch video, paste your channel ID or channel's link</li>
        <li>Use *A for positive comment and *B for negative comment</li>
    </ul>
    """, unsafe_allow_html=True)

    # Video input
    st.subheader("Enter Video Link:")
    video_link = st.text_input("Paste your video link here:")
    st.title("Enter your channel's link here")
    channel_link = st.text_input("Paste your channel's ID here:")

    # Display video if link is provided
    if video_link:
        st.video(video_link)

    # Text input
    st.subheader("Enter Text:")
    text_input = st.text_area("Enter your text here:")
    channel_ids = extract_channel_id(channel_link)
    pos_or_neg = comments_analyser(text_input)
    subscriber_channel_id = channel_ids
    target_channel_id = "UCFAG9pNumF0owhsM7Q70Z3Q"

    state = check_subscription("UCeud8r16gnTxJ8cycBWoubw", "UCFAG9pNumF0owhsM7Q70Z3Q")
    vote = 1

    # Display Save to CSV button
    if st.button("Save to CSV"):
        if video_link and text_input:
            if state == True and pos_or_neg == True:
                vote = 1 * (1.5)
            elif state == True and pos_or_neg == False:
                vote = 1 * (-1.5)
            elif state == False and pos_or_neg == True:
                vote = 1 * (1)
            elif state == False and pos_or_neg == False:
                vote = 1 * (-1)

            csv_path = save_to_csv(video_link, text_input, vote)
            st.success("Video link and text saved to CSV successfully!")

            # Add a download button for the CSV file
            st.download_button(
                label="Download CSV",
                data=pd.read_csv(csv_path).to_csv(index=False).encode('utf-8'),
                file_name=csv_path,
                mime='text/csv',
            )
        else:
            st.warning("Please enter both video link and text before saving.")


def tab3():
    st.title("Stripe Payment")

    if st.button('Pay with Stripe'):
        try:
            # Create a new checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': currency,
                            'product_data': {
                                'name': 'Sample Product',
                            },
                            'unit_amount': product_price,
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=domain_url + "/success",
                cancel_url=domain_url + "/cancel",
            )

            # Redirect to the URL for the checkout
            st.markdown(f"Please proceed to [payment]({checkout_session.url}) to complete your purchase.")

        except Exception as e:
            st.error(f"Error creating checkout session: {e}")

    # Define success page
    if 'success' in st.query_params:
        st.success("Payment completed successfully!")

    # Define cancel page
    if 'cancel' in st.query_params:
        st.error("Payment was cancelled.")


def main():
    st.title("YouTube Voting System")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    tabs = ["Dashboard", "Vote for a video", "Payment"]
    selected_tab = st.sidebar.radio("Select a role", tabs)

    if selected_tab == "Dashboard":
        api_key = 'AIzaSyBSj4DjGBkul0fHmzfLsOza9slvgu0C-G0'
        show_dashboard(api_key)

    elif selected_tab == "Vote for a video":
        tab2()
    elif selected_tab == "Payment":
        tab3()


if __name__ == "__main__":
    main()
