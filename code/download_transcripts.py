import argparse
import os
from datetime import datetime

import toml
from pymongo import MongoClient

# --- Configuration ---
SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloaded_transcripts")


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


def parse_date(date_str):
    """Parse date string in DD/MM/YYYY format to datetime object."""
    if date_str is None:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        print(f"Warning: Invalid date format '{date_str}'. Use DD/MM/YYYY format.")
        return None


def download_transcripts(
    min_duration=8, exclude_usernames=None, start_date=None, end_date=None
):
    """Fetches, filters, and saves transcripts to a single file.

    Args:
        min_duration: Minimum interview duration in minutes (default: 8)
        exclude_usernames: List of usernames to exclude (default: None)
        start_date: Start date filter in DD/MM/YYYY format (default: None)
        end_date: End date filter in DD/MM/YYYY format (default: None)
    """
    if exclude_usernames is None:
        exclude_usernames = []
    collection = get_db_collection()
    if collection is None:
        return

    # Create download directory if it doesn't exist
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"Created directory: {DOWNLOAD_DIR}")

    # Parse date filters
    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)

    all_interviews = list(collection.find({}))
    # Sort by start_time_unix descending (newest first)
    all_interviews.sort(key=lambda x: x.get("start_time_unix", 0), reverse=True)

    print(f"\nApplying filters:")
    print(
        f"  - Exclude usernames: {exclude_usernames if exclude_usernames else 'None'}"
    )
    print(f"  - Start date: {start_date if start_date else 'None'}")
    print(f"  - End date: {end_date if end_date else 'None'}")
    print(f"  - Min duration: {min_duration} minutes\n")

    filtered_interviews = []
    excluded_by_username = 0
    excluded_by_date = 0
    excluded_by_duration = 0

    for interview in all_interviews:
        username = interview.get("username", "")
        start_time_utc = interview.get("start_time_utc", "")

        # Filter by username
        if username in exclude_usernames:
            excluded_by_username += 1
            continue

        # Filter by date range
        if start_time_utc and (start_date_obj or end_date_obj):
            try:
                # Parse the interview start time (format: DD/MM/YYYY HH:MM:SS)
                interview_date = datetime.strptime(
                    start_time_utc.split()[0], "%d/%m/%Y"
                )

                if start_date_obj and interview_date < start_date_obj:
                    excluded_by_date += 1
                    continue

                if end_date_obj and interview_date > end_date_obj:
                    excluded_by_date += 1
                    continue
            except (ValueError, IndexError):
                print(
                    f"Warning: Could not parse date for {username} at {start_time_utc}"
                )

        # Check if interview has duration_minutes field (stored for completed interviews)
        duration_min = interview.get("duration_minutes")

        if duration_min:
            # duration_minutes is stored as a string, convert to float
            try:
                duration_value = float(duration_min)
                if duration_value >= min_duration:
                    interview["calculated_duration_minutes"] = duration_value
                    filtered_interviews.append(interview)
                else:
                    excluded_by_duration += 1
            except (ValueError, TypeError):
                print(
                    f"Warning: Invalid duration_minutes value for interview: {username} at {start_time_utc}"
                )
                excluded_by_duration += 1
        else:
            # Fallback: Calculate duration if end_time_unix exists (not last_updated_unix)
            start_unix = interview.get("start_time_unix")
            end_unix = interview.get("end_time_unix")  # Changed from last_updated_unix

            if start_unix and end_unix:
                duration_seconds = end_unix - start_unix
                duration_value = duration_seconds / 60
                if duration_value >= min_duration:
                    interview["calculated_duration_minutes"] = duration_value
                    filtered_interviews.append(interview)
                else:
                    excluded_by_duration += 1
            else:
                # If no duration info available, include only if min_duration is 0
                if min_duration == 0:
                    interview["calculated_duration_minutes"] = 0
                    filtered_interviews.append(interview)
                else:
                    excluded_by_duration += 1

    if not filtered_interviews:
        print(
            f"No interviews found with duration greater than or equal to {min_duration} minutes."
        )
        return

    print(f"\nFiltering results:")
    print(f"  - Total interviews in database: {len(all_interviews)}")
    print(f"  - Excluded by username: {excluded_by_username}")
    print(f"  - Excluded by date range: {excluded_by_date}")
    print(f"  - Excluded by duration: {excluded_by_duration}")
    print(f"  - Interviews to download: {len(filtered_interviews)}\n")

    output_filepath = os.path.join(DOWNLOAD_DIR, "all_transcripts.txt")

    try:
        with open(output_filepath, "w", encoding="utf-8") as f:
            for i, interview in enumerate(filtered_interviews):
                start_time_str = interview.get("start_time_utc", "N/A")
                duration_min = interview.get("calculated_duration_minutes", 0)

                username = interview.get("username", "N/A")
                f.write(f"--------------------\n")
                f.write(f"Interview {i + 1}\n")
                f.write(f"Username: {username}\n")
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
    parser = argparse.ArgumentParser(
        description="Download interview transcripts from MongoDB with optional filtering.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all interviews with default settings (min 8 minutes)
  python download_transcripts.py

  # Exclude user 'marco'
  python download_transcripts.py --exclude-usernames marco

  # Exclude multiple users
  python download_transcripts.py --exclude-usernames marco testuser admin

  # Filter by date range
  python download_transcripts.py --start-date 01/01/2024 --end-date 31/03/2024

  # Combine filters
  python download_transcripts.py --exclude-usernames marco --start-date 01/01/2024 --min-duration 10
        """,
    )

    parser.add_argument(
        "--min-duration",
        type=float,
        default=8,
        help="Minimum interview duration in minutes (default: 8)",
    )

    parser.add_argument(
        "--exclude-usernames",
        nargs="*",
        default=[],
        help="List of usernames to exclude (space-separated)",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date filter in DD/MM/YYYY format (e.g., 01/01/2024)",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="End date filter in DD/MM/YYYY format (e.g., 31/12/2024)",
    )

    args = parser.parse_args()

    download_transcripts(
        min_duration=args.min_duration,
        exclude_usernames=args.exclude_usernames,
        start_date=args.start_date,
        end_date=args.end_date,
    )
