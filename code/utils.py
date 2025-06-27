import streamlit as st
import hmac
import time
import os
from pymongo import MongoClient


# Password screen for dashboard (note: only very basic authentication!)
# Based on https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
def check_password():
    """Returns 'True' if the user has entered a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether username and password entered by the user are correct."""
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True

        else:
            st.session_state.password_correct = False

        del st.session_state.password  # don't store password in session state

    # Return True, username if password was already entered correctly before
    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    # Otherwise show login screen
    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username


def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists which signals that interview was completed."""

    # Test account has multiple interview attempts
    if username != "testaccount":

        # Check if file exists
        try:
            with open(os.path.join(directory, f"{username}.txt"), "r") as _:
                return True

        except FileNotFoundError:
            return False

    else:

        return False


def save_interview_data(
    username,
    transcripts_directory,
    times_directory,
    file_name_addition_transcript="",
    file_name_addition_time="",
):
    """Write interview data (transcript and time) to disk."""

    # Store chat transcript
    with open(
        os.path.join(
            transcripts_directory, f"{username}{file_name_addition_transcript}.txt"
        ),
        "w",
    ) as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    # Store file with start time and duration of interview
    with open(
        os.path.join(times_directory, f"{username}{file_name_addition_time}.txt"),
        "w",
    ) as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(
            f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\nInterview duration (minutes): {duration:.2f}"
        )


def save_interview_data_mongodb(username, system_prompt):
    """Write or update interview data in MongoDB."""

    try:
        # Get MongoDB credentials from Streamlit secrets
        mongo_uri = st.secrets["mongo"]["uri"]
        mongo_db = st.secrets["mongo"]["db"]
        mongo_collection = st.secrets["mongo"]["collection"]

        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db[mongo_collection]

        # Prepare transcript, excluding system message
        transcript_list = []
        for message in st.session_state.messages:
            if message["role"] != "system":
                transcript_list.append({"role": message["role"], "content": message["content"]})

        # Prepare data for MongoDB
        interview_data = {
            "last_updated_unix": time.time(),
            "last_updated_utc": time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time())),
            "transcript": transcript_list,
        }

        # If interview is inactive, add end time and duration
        if not st.session_state.get("interview_active", True):
            end_time = time.time()
            duration = (end_time - st.session_state.start_time) / 60
            interview_data["end_time_unix"] = end_time
            interview_data["end_time_utc"] = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(end_time))
            interview_data["duration_minutes"] = f"{duration:.2f}"

        # Use the unique combination of username and start_time as the filter for the document
        query = {
            "username": username,
            "start_time_unix": st.session_state.start_time
        }

        # Use $set to update fields, and $setOnInsert to set values only on creation
        update = {
            "$set": interview_data,
            "$setOnInsert": {
                "username": username,
                "start_time_unix": st.session_state.start_time,
                "start_time_utc": time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time)),
                "system_prompt": system_prompt,
            }
        }

        # Update the document, or insert it if it doesn't exist
        collection.update_one(query, update, upsert=True)

        # Close the connection
        client.close()

    except Exception as e:
        # In case of any error (e.g., secrets not configured), do not stop the app
        # Optionally, log the error for debugging
        # st.error(f"MongoDB connection error: {e}")
        pass
