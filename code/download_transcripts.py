import os
import toml
from pymongo import MongoClient

# --- Configuration ---
SECRETS_PATH = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloaded_transcripts')
MIN_DURATION_MINUTES = 8

def get_db_collection():
    """Reads secrets, connects to MongoDB, and returns the collection object."""
    try:
        secrets = toml.load(SECRETS_PATH)
        mongo_uri = secrets["mongo"]["uri"]
        mongo_db = secrets["mongo"]["db"]
        mongo_collection = secrets["mongo"]["collection"]

        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        return db[mongo_collection]
    except FileNotFoundError:
        print(f"Error: Secrets file not found at {SECRETS_PATH}")
        return None
    except (KeyError, Exception) as e:
        print(f"Error connecting to MongoDB or reading secrets: {e}")
        return None

def download_transcripts():
    """Fetches, filters, and saves transcripts to a single file."""
    collection = get_db_collection()
    if collection is None:
        return

    # Create download directory if it doesn't exist
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"Created directory: {DOWNLOAD_DIR}")

    all_interviews = list(collection.find({}))
    filtered_interviews = []
    min_duration_seconds = MIN_DURATION_MINUTES * 60

    for interview in all_interviews:
        start_unix = interview.get('start_time_unix')
        end_unix = interview.get('last_updated_unix')

        if start_unix and end_unix:
            duration_seconds = end_unix - start_unix
            if duration_seconds > min_duration_seconds:
                interview['calculated_duration_minutes'] = duration_seconds / 60
                filtered_interviews.append(interview)

    if not filtered_interviews:
        print(f"No interviews found with duration greater than {MIN_DURATION_MINUTES} minutes.")
        return

    print(f"Found {len(filtered_interviews)} interviews to save.")

    output_filepath = os.path.join(DOWNLOAD_DIR, "all_transcripts.txt")
    
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            for i, interview in enumerate(filtered_interviews):
                start_time_str = interview.get('start_time_utc', 'N/A')
                duration_min = interview.get('calculated_duration_minutes', 0)

                f.write(f"--------------------\n")
                f.write(f"Interview {i+1}\n")
                f.write(f"Date: {start_time_str}\n")
                f.write(f"Duration: {duration_min:.2f} minutes\n")
                f.write(f"--------------------\n\n")

                for message in interview.get("transcript", []):
                    if message.get("role") != "system":
                        role = message.get("role", "unknown_role").upper()
                        content = message.get("content", "").strip()
                        f.write(f"[{role}]\n{content}\n\n")
                f.write("\n")

        print(f"Successfully saved all transcripts to {output_filepath}")
    except IOError as e:
        print(f"Error writing to file {output_filepath}: {e}")

if __name__ == "__main__":
    download_transcripts()
