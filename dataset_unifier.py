import polars as pl
from issue_scraper import REPOS_TO_SCRAPE

MAX_LENGTH = 2000
MIN_LENGTH = 5

def load_and_combine(repo_owner, repo_name, data_path='./data'):
    issues_file = f"{data_path}/{repo_owner}_{repo_name}_issues.csv"
    comments_file = f"{data_path}/{repo_owner}_{repo_name}_comments.csv"

    issues_df = pl.read_csv(issues_file)
    comments_df = pl.read_csv(comments_file)

    # Correctly rename and add columns in comments_df
    comments_df = (comments_df
                   .rename({'date': 'timestamp', 'comment': 'text'})
                   .with_columns([
                       pl.lit('code_comment').alias('type'),
                       pl.lit(None).alias('status'),
                       pl.lit(None).alias('issue_id')
                   ]))
    
    issues_df = (issues_df.with_columns([pl.lit(f'{repo_owner}/{repo_name}').alias('repo')]))

    # Concatenate issues and comments
    combined_df = pl.concat([issues_df, comments_df], how='diagonal')

    return combined_df

# Combine data for all repositories
all_data = pl.concat([
    load_and_combine(repo_owner, repo_name)
    for repo_owner, repo_name in REPOS_TO_SCRAPE
], how='vertical')

# Filter out rows with text < 5 characters
all_data = all_data.filter(pl.col('text').str.lengths() > MIN_LENGTH)

# Now truncate text to 2000 characters in the combined dataset
all_data = all_data.with_columns([
    pl.when(pl.col('text').str.lengths() > MAX_LENGTH)
      .then(pl.col('text').str.slice(0, MAX_LENGTH))
      .otherwise(pl.col('text'))
      .alias('text')
])

# Load the star history data into Polars
star_history_df = pl.read_csv("./github_star_history.csv")

# Convert date columns to datetime, assuming the correct format is used
all_data = all_data.with_columns([
    pl.col('timestamp').str.replace("Z", "+00:00").str.strptime(pl.Datetime, '%Y-%m-%dT%H:%M:%S%z')
])
star_history_df = star_history_df.with_columns([
    pl.col('Date')
    .str.extract(r'(\w{3} \w{3} \d{2} \d{4})')
    .alias('extracted_date')  # Alias the extracted column for clarity
    .str.strptime(pl.Date, '%a %b %d %Y')
    .alias('Date')  # Rename the column back to 'Date' or use a new name as needed
])

import datetime

def interpolate_stars(repo, timestamp_date, star_history):
    # Ensure repo_star_history Date column is in date format if necessary
    repo_star_history = star_history.filter(pl.col('Repository') == repo)
    
    # Find the dates before and after the comment's date
    before = repo_star_history.filter(pl.col('Date').dt.date() <= timestamp_date).sort('Date', descending=True).limit(1)
    after = repo_star_history.filter(pl.col('Date').dt.date() >= timestamp_date).sort('Date').limit(1)

    if not before.is_empty() and not after.is_empty():
        # Extracting the first row as a dictionary and then get the values
        time_before, stars_before = before.select(['Date', 'Stars']).to_dicts()[0].values()
        time_after, stars_after = after.select(['Date', 'Stars']).to_dicts()[0].values()

        # Assuming time_before and time_after are datetime.date objects
        total_days_diff = (time_after - time_before).days
        days_diff = (timestamp_date - time_before).days

        star_diff = stars_after - stars_before
        interpolated_stars = stars_before + (star_diff * (days_diff / total_days_diff)) if total_days_diff != 0 else stars_before

        return interpolated_stars
    else:
        closest = before if not before.is_empty() else after
        return closest.select('Stars').to_series()[0] if not closest.is_empty() else None

repo_index = all_data.get_column_index('repo')
timestamp_index = all_data.get_column_index('timestamp')
# In your main script, where you map over all_data
all_data_with_stars = all_data.map_rows(
    lambda row: interpolate_stars(
        row[repo_index], 
        row[timestamp_index].date(),  # Directly use .date() here
        star_history_df
    )
)



# Now use these indices in map_rows
all_data_with_stars = all_data.map_rows(lambda row: interpolate_stars(row[repo_index], row[timestamp_index], star_history_df))

# Save the combined dataset to a CSV file
all_data_with_stars.write_csv("combined_dataset_with_stars.csv")
