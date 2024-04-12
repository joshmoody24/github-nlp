import pandas as pd
from issue_scraper import REPOS_TO_SCRAPE
from tqdm import tqdm

MAX_LENGTH = 2000
MIN_LENGTH = 5

def load_and_combine(repo_owner, repo_name, data_path='./data'):
    issues_file = f"{data_path}/{repo_owner}_{repo_name}_issues.csv"
    comments_file = f"{data_path}/{repo_owner}_{repo_name}_comments.csv"

    issues_df = pd.read_csv(issues_file)
    comments_df = pd.read_csv(comments_file)

    comments_df = comments_df.rename(columns={'date': 'timestamp', 'comment': 'text'})
    comments_df['type'] = 'code_comment'
    comments_df['status'] = None
    comments_df['issue_id'] = None
    comments_df['repo'] = f'{repo_owner}/{repo_name}'
    issues_df['repo'] = f'{repo_owner}/{repo_name}'

    combined_df = pd.concat([issues_df, comments_df], ignore_index=True)

    return combined_df

print("Loading and combining data...")
all_data = pd.concat([load_and_combine(repo_owner, repo_name) for repo_owner, repo_name in REPOS_TO_SCRAPE], ignore_index=True)

print("Filtering data...")
all_data = all_data[all_data['text'].str.len() > MIN_LENGTH]
all_data = all_data[all_data['text'].str.len() < MAX_LENGTH]

def special_chars_ratio(text):
    special_chars = "{}()[];<>+=-/*&|_#`"
    count = sum(1 for char in text if char in special_chars)
    return count / len(text)

def special_chars_count(text):
    special_chars = "{}()[];<>+=-/*&|_#`"
    return sum(1 for char in text if char in special_chars)

# filter out rows likely to be code
RATIO_THRESHOLD = 0.1
COUNT_THRESHOLD = 10
all_data['special_chars_ratio'] = all_data['text'].apply(special_chars_ratio)
all_data['special_chars_count'] = all_data['text'].apply(special_chars_count)
all_data = all_data[all_data['special_chars_ratio'] < RATIO_THRESHOLD]
all_data = all_data[all_data['special_chars_count'] < COUNT_THRESHOLD]

# remove duplicate text in the same repo, keeping the first occurrence
all_data = all_data.drop_duplicates(subset=['repo', 'text'], keep='first')

print("Converting timestamp in all_data to datetime...")
all_data['timestamp'] = pd.to_datetime(all_data['timestamp'], utc=True).dt.date

print("Loading star history data...")
star_history_df = pd.read_csv("./github_star_history.csv")

print("Converting Date in star_history_df to datetime...")
for i, date_str in enumerate(star_history_df['Date']):
    try:
        star_history_df.loc[i, 'Date'] = pd.to_datetime(date_str).date()
    except Exception as e:
        print(f"Error converting {date_str} to date: {e}")

def interpolate_stars(row, star_history):
    repo = row['repo']
    timestamp_date = row['timestamp']
    
    repo_star_history = star_history[star_history['Repository'] == repo]

    before = repo_star_history[repo_star_history['Date'] <= timestamp_date].sort_values('Date', ascending=False).head(1)
    after = repo_star_history[repo_star_history['Date'] >= timestamp_date].sort_values('Date').head(1)

    if not before.empty and not after.empty:
        # Ensure we only select the 'Date' and 'Stars' columns before unpacking
        time_before, stars_before = before[['Date', 'Stars']].iloc[0]
        time_after, stars_after = after[['Date', 'Stars']].iloc[0]

        total_days_diff = (time_after - time_before).days
        days_diff = (timestamp_date - time_before).days

        star_diff = stars_after - stars_before
        interpolated_stars = stars_before + (star_diff * (days_diff / total_days_diff)) if total_days_diff != 0 else stars_before

        return interpolated_stars.round().astype(int)
    else:
        closest = before if not before.empty else after
        return closest['Stars'].iloc[0] if not closest.empty else None
    
# print out 10 random rows to check
print("Random text samples:\n", all_data.sample(10)['text'], "\n")

# show number of rows per repo
print("Number of rows per repo:")
print(all_data['repo'].value_counts(), "\n")

print(f'Interpolating stars. Total rows: {len(all_data)}')
# Apply the interpolation function row-wise
tqdm.pandas()
all_data['interpolated_stars'] = all_data.progress_apply(lambda row: interpolate_stars(row, star_history_df), axis=1)

# drop special chars columns
all_data = all_data.drop(columns=['special_chars_ratio', 'special_chars_count'])

print("Saving to CSV...")
all_data.to_csv("combined_dataset_with_stars.csv", index=False)
