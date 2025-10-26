# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-led interview platform for conducting qualitative research. The platform uses OpenAI or Anthropic APIs to conduct structured interviews with respondents, focusing on topics like autonomy at work and AI's impact. The project is built with Streamlit and stores interview data both locally and optionally in MongoDB.

## Development Commands

### Environment Setup

**Using conda (recommended):**
```bash
cd code
conda env create -f interviewsenv.yml
conda activate interviews
```

**Using pip:**
```bash
cd code
pip install -r requirements.txt
```

### Running Applications

**Main interview application:**
```bash
cd code
streamlit run interview.py
```

**Browse transcripts (requires MongoDB):**
```bash
cd code
streamlit run browse_transcripts.py
```

**Download transcripts from MongoDB:**
```bash
cd code
python download_transcripts.py
```

### Testing Single Features

Run single Python modules for debugging:
```bash
cd code
python -c "from utils import check_password; print('Utils imported successfully')"
```

## Configuration

### API Keys and Secrets

Create `code/.streamlit/secrets.toml` (not tracked by git):
```toml
API_KEY_OPENAI = "your-openai-api-key"
API_KEY_ANTHROPIC = "your-anthropic-api-key"

[passwords]
PASSWORD = "your-password"

[mongo]
uri = "mongodb+srv://..."
db = "database-name"
collection = "collection-name"
```

### Model and Interview Configuration

Edit `code/config.py` to customize:
- `MODEL`: Choose between OpenAI models (e.g., "gpt-5") or Anthropic models (e.g., "claude-3-5-sonnet-20240620")
- `INTERVIEW_OUTLINE`: The structured interview script that guides the AI interviewer
- `GENERAL_INSTRUCTIONS`: Instructions for interview style (non-directive, open-ended questions)
- `TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `REASONING_EFFORT`: API parameters
- `LOGINS`: Enable/disable password protection

## Architecture

### Core Flow

1. **Session Initialization** (`interview.py`):
   - Validates user authentication via URL parameters (`?username=X&password=Y`)
   - Initializes Streamlit session state for messages and timing
   - Creates directories for data storage

2. **API Selection** (lines 13-23 in `interview.py`):
   - Detects API based on model name ("gpt" or "claude")
   - Loads appropriate client (OpenAI or Anthropic)
   - Note: OpenAI uses the Responses API with "developer" role instead of "system"

3. **Interview Execution**:
   - AI starts conversation based on `SYSTEM_PROMPT` (from `config.py`)
   - Messages stored in `st.session_state.messages`
   - Regular backups written to `data/backups/` after each exchange
   - Supports streaming (Anthropic) and non-streaming (OpenAI) responses

4. **Interview Termination**:
   - Triggered by special codes in AI responses (e.g., "x7y8" for normal end)
   - "Quit" button for manual termination
   - Final transcripts saved to `data/transcripts/` and `data/times/`

### Special Code System

The AI uses specific trigger codes (`config.CODES`) to signal different end states:
- `x7y8`: Normal interview completion
- `5j3k`: Problematic content detected
- `1y4x`: Depression cues detected

When these codes appear in the AI's response, they trigger predefined closing messages and stop the interview.

### Data Storage

**Dual storage architecture:**

1. **Local Files** (`utils.save_interview_data`):
   - Transcripts: `{username}.txt` with all messages
   - Times: `{username}.txt` with start time and duration
   - Backups: Timestamped files in `data/backups/`

2. **MongoDB** (`utils.save_interview_data_mongodb`):
   - Document per interview with upsert pattern
   - Unique key: combination of username + start_time_unix
   - Stores transcript array, metadata, timestamps
   - Gracefully fails if MongoDB not configured

### Transcript Management Tools

**browse_transcripts.py**:
- Password-protected web interface
- Displays interviews from MongoDB sorted by date
- Filter by username, navigate between transcripts
- Delete functionality with confirmation
- Download transcripts as .txt files

**download_transcripts.py**:
- Standalone script to export all transcripts from MongoDB
- Filters interviews by minimum duration (8 minutes default)
- Saves to `code/downloaded_transcripts/all_transcripts.txt`

## Important Notes

### Git Merge Conflicts

The `config.py` file contains unresolved git merge conflicts (lines 4-47). The interview outline has two versions between conflict markers. The second version (after `=======`) appears more structured with explicit phases (A, B, C, D, E). Resolve these conflicts before making changes to the interview outline.

### API Differences

- **OpenAI**: Uses Responses API, requires "developer" role instead of "system", non-streaming by default. Message history must be rebuilt before each API call to include the latest user message (fixed in interview.py:229-236).
- **Anthropic**: Uses Messages API with streaming, "system" parameter separate from messages. Uses direct reference to session state messages, so updates automatically.

### Password Protection

The authentication system is basic and relies on URL parameters. The README notes this is "only very basic authentication" - not suitable for sensitive data without additional security measures.

### MongoDB is Optional

All MongoDB operations use try/except blocks and silently fail if not configured. The platform works with just local file storage.

## File Structure

```
code/
├── interview.py              # Main interview application
├── config.py                 # Configuration and prompts
├── utils.py                  # Helper functions
├── browse_transcripts.py     # Web UI for viewing transcripts
├── download_transcripts.py   # Script to export from MongoDB
├── requirements.txt          # Python dependencies
├── interviewsenv.yml         # Conda environment
└── .streamlit/
    └── secrets.toml          # API keys (not in git)

data/
├── transcripts/              # Final interview transcripts
├── times/                    # Interview timing data
└── backups/                  # Incremental backups during interviews
```
