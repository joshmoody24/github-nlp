import git
import csv
import re
import os
import tqdm
from issue_scraper import REPOS_TO_SCRAPE

COMMENT_PATTERNS = {
    '.py': [
        r'^\s*#(.*)',        # Python comments
        r'"""([\s\S]*?)"""', # Python multiline strings
        r"'''([\s\S]*?)'''"  # Python multiline strings
    ],
    '.c': [
        r'//(.*)',           # C/C++/C#/Java/JavaScript single-line comments
        r'/\*([\s\S]*?)\*/'  # C multiline comments
    ],
    '.cpp': [
        r'//(.*)',           # C++ single-line comments
        r'/\*([\s\S]*?)\*/'  # C++ multiline comments
    ],
    '.cs': [
        r'//(.*)',           # C# single-line comments
        r'/\*([\s\S]*?)\*/'  # C# multiline comments
    ],
    '.js': [
        r'//(.*)',           # JavaScript single-line comments
        r'/\*([\s\S]*?)\*/'  # JavaScript multiline comments
    ],
    '.sh': [
        r'^\s*#(.*)'         # Shell comments
    ],
    '.java': [
        r'//(.*)',           # Java single-line comments
        r'/\*([\s\S]*?)\*/'  # Java multiline comments
    ],
    '.ex': [
        r'^\s*#(.*)'         # Elixir single-line comments
    ],
    '.exs': [
        r'^\s*#(.*)'         # Elixir single-line comments
    ],
    '.go': [
        r'//(.*)',           # Go single-line comments
        r'/\*([\s\S]*?)\*/'  # Go multiline comments
    ],
    '.ts': [
        r'//(.*)',           # TypeScript single-line comments
        r'/\*([\s\S]*?)\*/'  # TypeScript multiline comments
    ],
    '.php': [
        r'//(.*)',           # PHP single-line comments
        r'/\*([\s\S]*?)\*/', # PHP multiline comments
        r'^\s*#(.*)'         # PHP shell-style comments
    ],
    '.rb': [
        r'^\s*#(.*)'         # Ruby single-line comments
    ],
    '.swift': [
        r'//(.*)',           # Swift single-line comments
        r'/\*([\s\S]*?)\*/'  # Swift multiline comments
    ]
}

def clone_repo(repo_owner, repo_name):
    if os.path.exists(f'./repos/{repo_name}'):
        print(f'Repo {repo_owner}/{repo_name} already cloned')
        return git.Repo(f'./repos/{repo_name}')
    print(f'Cloning {repo_owner}/{repo_name}')
    repo_path = f'./repos/{repo_name}'
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)
    git_url = f'https://github.com/{repo_owner}/{repo_name}.git'
    repo = git.Repo.clone_from(git_url, repo_path)
    return repo

def is_source_code(file_path):
    return file_path.endswith(('.py', '.c', '.cpp', '.cs', '.js', '.sh', '.java'))

def extract_comments(repo_owner, repo_name):
    repo = clone_repo(repo_owner, repo_name)
    csv_data = []

    for commit in tqdm.tqdm(repo.iter_commits(), desc='Extracting comments from commits'):
        if not commit.parents:
            continue  # Skip initial commit as it has no parent to compare with
        diff = commit.diff(commit.parents[0], create_patch=True)

        for blob_diff in diff:
            if blob_diff.b_path is None or not is_source_code(blob_diff.b_path):
                continue

            file_ext = os.path.splitext(blob_diff.b_path)[1]
            patterns = COMMENT_PATTERNS.get(file_ext, [])

            added_lines = [line[1:] for line in blob_diff.diff.decode('utf-8', errors='ignore').split('\n') if line.startswith('+')]
            added_code = '\n'.join(added_lines)

            for pattern in patterns:
                matches = re.finditer(pattern, added_code, re.MULTILINE)
                for match in matches:
                    comment = match.group(1).strip()
                    csv_data.append({'repo': f'{repo_owner}/{repo_name}', 'date': commit.committed_datetime.isoformat(), 'comment': comment})

    with open(f'./data/{repo_owner}_{repo_name}_comments.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['repo', 'date', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_data:
            writer.writerow(row)

if __name__ == '__main__':
    for repo_owner, repo_name in REPOS_TO_SCRAPE:
        extract_comments(repo_owner, repo_name)
