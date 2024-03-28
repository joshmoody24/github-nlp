import pandas as pd
from issue_scraper import REPOS_TO_SCRAPE

MAX_LENGTH = 1000
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

    combined_df = pd.concat([issues_df, comments_df], ignore_index=True)

    return combined_df

all_data = pd.concat([load_and_combine(repo_owner, repo_name) for repo_owner, repo_name in REPOS_TO_SCRAPE], ignore_index=True)

all_data = all_data[all_data['text'].str.len() > MIN_LENGTH]
all_data = all_data[all_data['text'].str.len() < MAX_LENGTH]

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

        return round(interpolated_stars)
    else:
        closest = before if not before.empty else after
        return closest['Stars'].iloc[0] if not closest.empty else None

print(f'Interpolating stars. Total rows: {len(all_data)}')
# Apply the interpolation function row-wise
all_data['interpolated_stars'] = all_data.apply(lambda row: interpolate_stars(row, star_history_df), axis=1)

print("Saving to CSV...")
all_data.to_csv("combined_dataset_with_stars.csv", index=False)
