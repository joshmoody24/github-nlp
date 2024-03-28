import requests
import re
import time
import tqdm
from dotenv import load_dotenv
import os

load_dotenv()

REPOS_TO_SCRAPE = [
    # smaller repos
    ('joshmoody24', 'sitcom-simulator'),
    ('nodejs', 'nodejs.org'),
    ('spacejam', 'sled'),
    ('Auto1111SDK', 'Auto1111SDK'),
    ('stitionai', 'devika'),
    ('zzzprojects', 'System.Linq.Dynamic.Core'),

    # larger repos
    ('pallets', 'flask'),
    ('facebook', 'react'),
    ('hotwired', 'turbo'),
    ('rails', 'rails'),
    ('vuejs', 'core'),
    ('Zulko', 'moviepy'),
    ('withastro', 'astro'),
    ('bigskysoftware', 'htmx'),
    ('phoenixframework', 'phoenix'),
    ('ethereum', 'go-ethereum'),
    ('twbs', 'bootstrap'),
    ('django', 'django'),
    ('microsoft', 'vscode'),
]

PAGE_SIZE = 100
NEXT_REGEX = r'(?<=<)([\S]*)(?=>; rel=\"next\")'
LAST_PAGE_REGEX = r'(?<=<)[\S]*page=(\d+)(?=>; rel="last")'
REQUESTS_PER_HOUR = 5000
REQUEST_DELAY = (3600 / REQUESTS_PER_HOUR) + 0.05

if not os.getenv("GH_TOKEN"):
    raise Exception("GH_TOKEN not found in environment variables")

headers = {
    'Authorization': f'Bearer {os.getenv("GH_TOKEN")}',
}

def get_sleep_time(last_request_time):
    return max(0, REQUEST_DELAY - (time.time() - last_request_time)), time.time()

def extract_text_from_repo_issues(repo_owner, repo_name):
    issue_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/issues?per_page={PAGE_SIZE}'
    last_request_time = time.time()
    first_page = requests.get(issue_url, headers=headers)
    first_page_link = first_page.headers.get('link', '')
    last_page_num = int(re.search(LAST_PAGE_REGEX, first_page_link).group(1)) if 'rel="last"' in first_page_link else 1
    issue_rows = []
    has_more_issues = True
    total_issues = last_page_num * PAGE_SIZE if last_page_num > 1 else len(first_page.json())
    with tqdm.tqdm(total=total_issues) as pbar:
        pbar.set_description(f'Scraping {repo_name} issues')
        while has_more_issues:
            sleep_seconds, last_request_time = get_sleep_time(last_request_time)
            time.sleep(sleep_seconds)
            response = requests.get(issue_url, headers=headers)
            issues = response.json()
            
            for issue in issues:
                if(type(issue) != dict):
                    print(issues)
                    continue
                if issue['body']:
                    issue_rows.append({
                        'issue_id': issue['id'],
                        'timestamp': issue['created_at'],
                        'type': 'issue_body',
                        'text': issue['body'],
                        'status': issue['state'],
                    })
                comments_url = issue['comments_url'] + f'?per_page={PAGE_SIZE}'
                has_more_comments = True
                while has_more_comments:
                    sleep_seconds, last_request_time = get_sleep_time(last_request_time)
                    time.sleep(sleep_seconds)
                    comments_response = requests.get(comments_url, headers=headers)
                    comments = comments_response.json()
                    for comment in comments:
                        if type(comment) != dict:
                            print(comments)
                            continue
                        if comment['body']:
                            issue_rows.append({
                                'issue_id': issue['id'],
                                'timestamp': comment['created_at'],
                                'type': 'issue_comment',
                                'text': comment['body'],
                                'status': issue['state'],
                            })
                    if 'rel="next"' in comments_response.headers.get('link', ''):
                        next_url = re.search(NEXT_REGEX, comments_response.headers['link']).group(0)
                        comments_url = next_url
                    else:
                        has_more_comments = False

                pbar.update(1)
            
            if 'rel="next"' in response.headers.get('link', ''):
                next_url = re.search(NEXT_REGEX, response.headers['link']).group(0)
                issue_url = next_url
            else:
                has_more_issues = False

    if not os.path.exists('./data'):
        os.makedirs('./data')
    import csv
    with open(f'./data/{repo_owner}_{repo_name}_issues.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'type', 'status', 'text', 'issue_id'])
        writer.writeheader()
        writer.writerows(issue_rows)

if __name__ == '__main__':
    for repo_owner, repo_name in REPOS_TO_SCRAPE:
        try:
            extract_text_from_repo_issues(repo_owner, repo_name)
        except Exception as e:
            print(f'Error scraping {repo_name}: {e}')
            import traceback
            traceback.print_exc()