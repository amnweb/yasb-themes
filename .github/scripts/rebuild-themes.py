import os
import json
import subprocess
from datetime import datetime

THEMES_FOLDER = './themes'
THEMES_DATA_FILE = './themes.json'

def get_last_commit_date(folder):
    try:
        # Get the last commit date for the folder
        result = subprocess.run(['git', 'log', '-1', '--format=%ct', folder], capture_output=True, text=True, check=True)
        timestamp = int(result.stdout.strip())
        commit_date = datetime.fromtimestamp(timestamp)
        return commit_date
    except subprocess.CalledProcessError as e:
        print(f"Error getting last commit date for {folder}: {e}")
        return None

def sort_folders_by_commit_date(folders):
    folder_commit_dates = {}
    for folder in folders:
        commit_date = get_last_commit_date(folder)
        if commit_date:
            folder_commit_dates[folder] = commit_date
        else:
            # If no commit date is found, use a very old date to push it to the end
            folder_commit_dates[folder] = datetime.min
    sorted_folders = sorted(folder_commit_dates.keys(), key=lambda f: folder_commit_dates[f], reverse=True)
    return sorted_folders

def main():
    with open(THEMES_DATA_FILE, 'w') as f:
        json.dump({}, f, indent=4)
    
    theme_folders = [os.path.join(THEMES_FOLDER, theme) for theme in os.listdir(THEMES_FOLDER) if os.path.isdir(os.path.join(THEMES_FOLDER, theme))]
    sorted_theme_folders = sort_folders_by_commit_date(theme_folders)
    
    for theme_folder in sorted_theme_folders:
        theme = os.path.basename(theme_folder)
        theme_data_file = os.path.join(theme_folder, 'theme.json')
        if not os.path.exists(theme_data_file):
            continue
        with open(theme_data_file, 'r') as f:
            theme_data = json.load(f)
            with open(THEMES_DATA_FILE, 'r') as f:
                themes_data = json.load(f)
                themes_data[theme] = theme_data
                with open(THEMES_DATA_FILE, 'w') as f:
                    json.dump(themes_data, f, indent=4)
                    del themes_data
        print(f"Rebuilt theme: {theme}")
    print("Rebuilt all themes!")
  
if __name__ == '__main__':
    main()
