# NOTE: this file is unused because GitHub API only supports most recent 40000 stars. Using star-history website instead.

from issue_scraper import REPOS_TO_SCRAPE, REQUEST_DELAY, NEXT_REGEX, PAGE_SIZE, LAST_PAGE_REGEX, get_sleep_time
from dotenv import load_dotenv
import os
import requests
import csv
import tqdm
import re
import time

load_dotenv()

def get_star_history(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/stargazers?per_page={PAGE_SIZE}'
    headers = {
        'Authorization': f'token {os.getenv("GH_TOKEN")}',
        'Accept': 'application/vnd.github.v3.star+json'
    }
    first_page = requests.get(url, headers=headers)
    first_page_link = first_page.headers.get('link', '')
    last_page_num = int(re.search(LAST_PAGE_REGEX, first_page_link).group(1)) if 'rel="last"' in first_page_link else 1
    last_request_time = time.time()
    has_more_pages = True
    stargazers = []
    with tqdm.tqdm(total=last_page_num) as pbar:
        pbar.set_description(f'Scraping {repo} stargazers')
        while has_more_pages:
            sleep_seconds, last_request_time = get_sleep_time(last_request_time)
            time.sleep(sleep_seconds)
            response = requests.get(url, headers=headers)
            stargazers += response.json()
            pbar.update(1)
            if 'rel="next"' in response.headers.get('link', ''):
                url = re.search(NEXT_REGEX, response.headers['link']).group(0)
            else:
                has_more_pages = False
        response = requests.get(url, headers=headers)
        return stargazers

def save_to_csv(repo_owner, repo_name, star_history):
    print(f"Saving star history for {repo_owner}/{repo_name} to CSV...")
    # format: user_name, starred_at, cumulative_stars (running total of stars at that time)
    # all sorted by starred_at
    if not os.path.exists('./data'):
        os.makedirs('./data')
    with open(f'./data/{repo_owner}_{repo_name}_stars.csv', 'w', newline='') as csvfile:
        star_history = sorted(star_history, key=lambda x: x['starred_at'])
        for i, star in enumerate(star_history):
            star['cumulative_stars'] = i + 1
        fieldnames = ['user_name', 'starred_at', 'cumulative_stars']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for star in star_history:
            writer.writerow({
                'user_name': star['user']['login'],
                'starred_at': star['starred_at'],
                'cumulative_stars': star['cumulative_stars']
            })

if __name__ == '__main__':
    for repo, owner in REPOS_TO_SCRAPE:
        star_history = get_star_history(repo, owner)
        save_to_csv(repo, owner, star_history)