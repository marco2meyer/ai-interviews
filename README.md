# Code for "Conversations at Scale: Robust AI-led Interviews with a Simple Open-Source Platform"

There are two options to explore the AI-led interviews discussed in the paper.

## Option 1: Online notebook

To try own ideas for interviews within minutes and without the need to install Python, see https://colab.research.google.com/drive/1sYl2BMiZACrOMlyASuT-bghCwS5FxHSZ (requires to obtain an API key)

## Option 2: Full platform

To install Python and set up the full interview platform locally (takes around 1h from scratch), see the following steps.

The interview platform is built using the library `streamlit` and the APIs of OpenAI and Anthropic.

- Download miniconda from https://docs.anaconda.com/miniconda/miniconda-install/ and install it (skip if `conda` is already installed)
- Obtain an API key from https://platform.openai.com/ or https://www.anthropic.com/api. In case of the OpenAI API, choose a "project" key
- Download this repository
- In the repository folder on your computer, paste your API key into the file `/code/.streamlit/secrets.toml` (requires to make hidden folders visible)
- In the config.py, select a language model and adjust the interview outline
- In Terminal (Mac) or Anaconda Prompt (Windows), navigate to the folder `code` with `cd` (if unclear, briefly look up basic Linux command line syntax for navigating to folders)
- Once in the `code` folder, create the environment from the .yml file by writing `conda env create -f interviewsenv.yml` and confirming with enter (this installs Python and all libraries necessary to run the platform; only needs to be done once)
- Activate the environment with `conda activate interviews`
- Start the platform with `streamlit run interview.py`

## Downloading transcripts from MongoDB

The platform includes a script to download and filter interview transcripts from MongoDB to a single text file.

### Basic usage

```bash
cd code
conda activate interviews
python download_transcripts.py
```

This downloads all interviews with a duration of at least 8 minutes to `code/downloaded_transcripts/all_transcripts.txt`.

### Filtering options

**Exclude specific usernames:**
```bash
python download_transcripts.py --exclude-usernames marco
```

**Exclude multiple users:**
```bash
python download_transcripts.py --exclude-usernames marco testuser admin
```

**Filter by date range:**
```bash
python download_transcripts.py --start-date 01/01/2024 --end-date 31/03/2024
```

**Set minimum duration:**
```bash
python download_transcripts.py --min-duration 10
```

**Combine multiple filters:**
```bash
python download_transcripts.py --exclude-usernames marco --start-date 01/01/2024 --end-date 31/03/2024 --min-duration 10
```

**Get help:**
```bash
python download_transcripts.py --help
```

### Command-line options

- `--min-duration`: Minimum interview duration in minutes (default: 8)
- `--exclude-usernames`: Space-separated list of usernames to exclude
- `--start-date`: Start date in DD/MM/YYYY format (e.g., 01/01/2024)
- `--end-date`: End date in DD/MM/YYYY format (e.g., 31/12/2024)


## Paper and citation

The paper is available at https://ssrn.com/abstract=4974382 and can be cited with the following bibtex entry:

```
@article{geieckejaravel2024,
  title={Conversations at Scale: Robust AI-led Interviews with a Simple Open-Source Platform},
  author={Geiecke, Friedrich and Jaravel, Xavier},
  url={https://ssrn.com/abstract=4974382},
  year={2024}
}
```
