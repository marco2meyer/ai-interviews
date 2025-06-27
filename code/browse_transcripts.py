import streamlit as st
from pymongo import MongoClient
import pandas as pd
import time
import config
import hmac

# Set page config
st.set_page_config(page_title="Transcript Browser", page_icon="📂", layout="wide")

st.title("📂 Transcript Browser")

# --- Password Protection ---
try:
    query_params = st.query_params
    url_password = query_params.get("password")
    secret_password = st.secrets["passwords"]["PASSWORD"]

    if not (url_password and hmac.compare_digest(url_password, secret_password)):
        st.error("Invalid or missing password in URL parameter 'password'.")
        st.stop()
except (KeyError, AttributeError):
    st.error("`PASSWORD` not configured in Streamlit secrets or password not provided in URL.")
    st.stop()

# --- Database Connection ---
@st.cache_resource
def get_mongo_collection():
    """Connects to MongoDB and returns the collection object."""
    try:
        mongo_uri = st.secrets["mongo"]["uri"]
        mongo_db = st.secrets["mongo"]["db"]
        mongo_collection = st.secrets["mongo"]["collection"]
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        return db[mongo_collection]
    except Exception as e:
        st.error(f"Failed to connect to MongoDB. Please check your secrets.toml file. Error: {e}")
        return None

@st.cache_data
def load_transcripts(_collection):
    """Loads all transcripts from the collection and sorts them by start time."""
    if _collection is not None:
        transcripts = list(_collection.find({}))
        if transcripts:
            # Sort by start_time_unix descending (newest first)
            return sorted(transcripts, key=lambda x: x.get('start_time_unix', 0), reverse=True)
    return []

collection = get_mongo_collection()
if collection is None:
    st.stop()

# --- Main Application ---
transcripts = load_transcripts(collection)

if not transcripts:
    st.warning("No transcripts found in the database.")
    st.stop()

# Initialize session state for the index
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- Sidebar for Navigation and Filtering ---
with st.sidebar:
    st.header("Navigation")

    # 5. Filter by username
    usernames = ["All"] + sorted(list(set(t['username'] for t in transcripts)))
    selected_username = st.selectbox("Filter by Username:", usernames)

    # Filter transcripts based on selection
    if selected_username == "All":
        filtered_transcripts = transcripts
    else:
        filtered_transcripts = [t for t in transcripts if t['username'] == selected_username]

    if not filtered_transcripts:
        st.warning(f"No transcripts found for user: {selected_username}")
        st.stop()

    total_transcripts = len(filtered_transcripts)

    # Reset index if the filter changes
    if 'last_filter' not in st.session_state or st.session_state.last_filter != selected_username:
        st.session_state.current_index = 0
        st.session_state.last_filter = selected_username

    # 4. Display current conversation number
    st.write(f"Showing conversation **{st.session_state.current_index + 1}** of **{total_transcripts}**")

    # 3. Select conversation by number
    new_index = st.number_input("Go to conversation:", min_value=1, max_value=total_transcripts, value=st.session_state.current_index + 1) - 1
    if new_index != st.session_state.current_index:
        st.session_state.current_index = new_index

    # 2. Buttons to go back and forth
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Previous", use_container_width=True, disabled=st.session_state.current_index <= 0):
        st.session_state.current_index -= 1
        st.rerun()

    if col2.button("Next ➡️", use_container_width=True, disabled=st.session_state.current_index >= total_transcripts - 1):
        st.session_state.current_index += 1
        st.rerun()

    # --- Delete Section ---
    st.divider()
    st.error("Danger Zone")

    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False

    if st.session_state.confirm_delete:
        conversation_to_delete = filtered_transcripts[st.session_state.current_index]
        st.warning(f"Are you sure you want to delete the transcript for **{conversation_to_delete.get('username')}** from **{conversation_to_delete.get('start_time_utc')}**?")
        
        c1, c2 = st.columns(2)
        if c1.button("✅ Yes, delete it", use_container_width=True, key="confirm_delete_button"):
            collection.delete_one({'_id': conversation_to_delete['_id']})
            load_transcripts.clear()
            st.session_state.current_index = 0
            st.session_state.confirm_delete = False
            st.success("Transcript deleted successfully.")
            time.sleep(1)
            st.rerun()
            
        if c2.button("❌ Cancel", use_container_width=True, key="cancel_delete_button"):
            st.session_state.confirm_delete = False
            st.rerun()
    else:
        if st.button("🗑️ Delete Transcript", use_container_width=True, key="delete_button"):
            st.session_state.confirm_delete = True
            st.rerun()

# --- Display Selected Conversation ---

# 1. Standardly display the last conversation (index 0 of sorted list)
if 0 <= st.session_state.current_index < total_transcripts:
    conversation = filtered_transcripts[st.session_state.current_index]

    # Display key metadata
    col1, col2, col3 = st.columns(3)
    col1.metric("Username", conversation.get('username', 'N/A'))
    col2.metric("Start Time (UTC)", conversation.get('start_time_utc', 'N/A'))
    col3.metric("Duration (minutes)", conversation.get('duration_minutes', 'N/A'))
    st.divider()

    st.subheader("Transcript")
    for message in conversation.get("transcript", []):
        role = message.get("role")
        content = message.get("content")
        if role == "assistant":
            avatar = config.AVATAR_INTERVIEWER
        else:
            avatar = config.AVATAR_RESPONDENT
        with st.chat_message(role, avatar=avatar):
            st.markdown(content)

    # 6. Show all metadata
    with st.expander("Metadata", expanded=False):
        # To improve readability, we can convert the MongoDB object to a more readable format
        display_meta = {k: v for k, v in conversation.items() if k not in ['transcript', '_id']}
        st.json(display_meta, expanded=True)

    # 7. Allow to download the transcript
    def format_transcript_for_download(conv):
        lines = []
        for key, value in conv.items():
            if key != 'transcript' and key != '_id':
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        lines.append("\n---\nTranscript\n---")
        for msg in conv.get("transcript", []):
            lines.append(f"\n[{msg.get('role')}]\n{msg.get('content')}")
        return "\n".join(lines)

    file_content = format_transcript_for_download(conversation)
    start_time_str = conversation.get('start_time_utc', 'unknown_time').replace('/', '-').replace(':', '-')
    end_time_str = conversation.get('end_time_utc', 'unknown_time').replace('/', '-').replace(':', '-')
    file_name = f"{conversation.get('username', 'user')}_{start_time_str}_to_{end_time_str}.txt"

    st.sidebar.download_button(
        label="Download Transcript",
        data=file_content,
        file_name=file_name,
        mime="text/plain",
        use_container_width=True
    )

else:
    st.error("Could not find the selected transcript.")
