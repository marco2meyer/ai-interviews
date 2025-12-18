import os
from collections import Counter

import toml
from pymongo import MongoClient

# --- Configuration ---
SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")


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


def diagnose_database():
    """Analyzes the database to understand what fields exist and their values."""
    collection = get_db_collection()
    if collection is None:
        return

    all_interviews = list(collection.find({}))
    total = len(all_interviews)

    print(f"\n{'=' * 60}")
    print(f"DATABASE DIAGNOSIS")
    print(f"{'=' * 60}\n")
    print(f"Total interviews in database: {total}\n")

    # Check which fields exist
    has_duration_minutes = 0
    has_end_time_unix = 0
    has_last_updated_unix = 0
    has_start_time_unix = 0

    duration_values = []
    interviews_with_valid_duration = []
    interviews_without_duration = []

    for interview in all_interviews:
        username = interview.get("username", "unknown")
        start_time = interview.get("start_time_utc", "unknown")

        if "duration_minutes" in interview:
            has_duration_minutes += 1
            try:
                duration_val = float(interview["duration_minutes"])
                duration_values.append(duration_val)
                if duration_val >= 8:
                    interviews_with_valid_duration.append(
                        (username, start_time, duration_val)
                    )
            except (ValueError, TypeError):
                print(
                    f"  Warning: Invalid duration_minutes for {username} at {start_time}"
                )
        else:
            interviews_without_duration.append((username, start_time))

        if "end_time_unix" in interview:
            has_end_time_unix += 1
        if "last_updated_unix" in interview:
            has_last_updated_unix += 1
        if "start_time_unix" in interview:
            has_start_time_unix += 1

    print(f"Field presence:")
    print(
        f"  - start_time_unix:     {has_start_time_unix}/{total} ({100 * has_start_time_unix / total:.1f}%)"
    )
    print(
        f"  - last_updated_unix:   {has_last_updated_unix}/{total} ({100 * has_last_updated_unix / total:.1f}%)"
    )
    print(
        f"  - end_time_unix:       {has_end_time_unix}/{total} ({100 * has_end_time_unix / total:.1f}%)"
    )
    print(
        f"  - duration_minutes:    {has_duration_minutes}/{total} ({100 * has_duration_minutes / total:.1f}%)"
    )

    print(f"\n{'=' * 60}")
    print(f"DURATION ANALYSIS")
    print(f"{'=' * 60}\n")

    if duration_values:
        print(f"Interviews with duration_minutes field: {len(duration_values)}")
        print(f"  - Min duration: {min(duration_values):.2f} minutes")
        print(f"  - Max duration: {max(duration_values):.2f} minutes")
        print(
            f"  - Average duration: {sum(duration_values) / len(duration_values):.2f} minutes"
        )
        print(f"  - With duration >= 8 minutes: {len(interviews_with_valid_duration)}")

    print(
        f"\nInterviews WITHOUT duration_minutes field: {len(interviews_without_duration)}"
    )
    if interviews_without_duration:
        print(f"\nFirst 10 interviews missing duration_minutes:")
        for username, start_time in interviews_without_duration[:10]:
            print(f"  - {username} at {start_time}")
        if len(interviews_without_duration) > 10:
            print(f"  ... and {len(interviews_without_duration) - 10} more")

    print(f"\n{'=' * 60}")
    print(f"DOWNLOAD SCRIPT SIMULATION")
    print(f"{'=' * 60}\n")

    # Simulate old logic (using last_updated_unix)
    old_logic_count = 0
    for interview in all_interviews:
        start_unix = interview.get("start_time_unix")
        end_unix = interview.get("last_updated_unix")
        if start_unix and end_unix:
            duration_seconds = end_unix - start_unix
            if duration_seconds > 8 * 60:
                old_logic_count += 1

    # Simulate new logic (using duration_minutes or end_time_unix)
    new_logic_count = 0
    for interview in all_interviews:
        duration_min = interview.get("duration_minutes")
        if duration_min:
            try:
                if float(duration_min) >= 8:
                    new_logic_count += 1
            except (ValueError, TypeError):
                pass
        else:
            start_unix = interview.get("start_time_unix")
            end_unix = interview.get("end_time_unix")
            if start_unix and end_unix:
                duration_seconds = end_unix - start_unix
                if duration_seconds >= 8 * 60:
                    new_logic_count += 1

    print(
        f"OLD logic (using last_updated_unix): {old_logic_count} interviews would be downloaded"
    )
    print(
        f"NEW logic (using duration_minutes/end_time_unix): {new_logic_count} interviews would be downloaded"
    )
    print(f"Difference: {new_logic_count - old_logic_count} more interviews\n")

    # Sort interviews by start_time_unix to see newest
    sorted_interviews = sorted(
        all_interviews, key=lambda x: x.get("start_time_unix", 0), reverse=True
    )

    print(f"{'=' * 60}")
    print(f"NEWEST 5 INTERVIEWS")
    print(f"{'=' * 60}\n")

    for i, interview in enumerate(sorted_interviews[:5]):
        username = interview.get("username", "unknown")
        start_time = interview.get("start_time_utc", "unknown")
        duration = interview.get("duration_minutes", "N/A")
        has_end = "end_time_unix" in interview
        has_duration = "duration_minutes" in interview

        print(f"{i + 1}. {username} - {start_time}")
        print(f"   Duration: {duration} minutes")
        print(f"   Has end_time_unix: {has_end}")
        print(f"   Has duration_minutes: {has_duration}")
        if has_duration:
            try:
                if float(duration) >= 8:
                    print(f"   Would be INCLUDED in download")
                else:
                    print(f"   Would be EXCLUDED (duration < 8 min)")
            except:
                print(f"   Would be EXCLUDED (invalid duration)")
        else:
            print(f"   Would be EXCLUDED (no duration_minutes field)")
        print()


if __name__ == "__main__":
    diagnose_database()
