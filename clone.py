import subprocess
import pandas as pd
import os
from pathlib import Path


MAX_REPO_SIZE = 2000
MAX_COUNT_REPOS = 100


repos_path_prefix = Path("data/data/")

lang_repo = {
    "go": Path("golang_repos.csv"),
    "java": Path("java_repos.csv"),
    "javascript": Path("javascript_repos.csv"),
    "python": Path("python_repos.csv"),
    "typescript": Path("typescript_repos.csv"),
    "kotlin": Path("kotlin_repos.csv"),
}


def load_repos(lang: str) -> pd.DataFrame:
    repo_path = repos_path_prefix / lang_repo[lang]
    df = pd.read_csv(repo_path)
    return df


def clone_repo(repo_url: str, target_dir: Path) -> None:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    clone_path = target_dir / repo_name
    if not clone_path.exists():
        subprocess.run(["git", "clone", repo_url, str(clone_path)])
        print(f"Cloned {repo_name} into {clone_path}")


def main():
    for lang in lang_repo:
        repos = load_repos(lang)
        target_path = Path(f"sample/{lang}")
        os.makedirs(target_path, exist_ok=True)
        print(f"Cloning {lang} repositories...")
        cnt = 0
        for _, repo in repos.iterrows():
            if cnt >= MAX_COUNT_REPOS:
                break

            if repo["size"] <= MAX_REPO_SIZE:
                cnt += 1
                repo_url = repo["url"]
                clone_repo(repo_url, target_path)


if __name__ == "__main__":
    main()
