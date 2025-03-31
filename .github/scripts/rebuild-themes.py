import os
import json
from datetime import datetime

THEMES_FOLDER = './themes'
THEMES_DATA_FILE = './themes.json'

def get_publish_date_from_theme(folder):
    theme_data_file = os.path.join(folder, 'theme.json')
    if os.path.exists(theme_data_file):
        try:
            with open(theme_data_file, 'r') as f:
                theme_data = json.load(f)
                if 'publish_date' in theme_data:
                    return datetime.fromisoformat(theme_data['publish_date'])
        except Exception as e:
            print(f"Error reading publish_date for {folder}: {e}")
    return datetime.min

def sort_folders_by_publish_date(folders):
    sorted_folders = sorted(folders, key=lambda f: get_publish_date_from_theme(f), reverse=True)
    return sorted_folders

def main():
    # Initialize themes.json to empty dict
    with open(THEMES_DATA_FILE, 'w') as f:
        json.dump({}, f, indent=4)
    
    # List the theme folders
    theme_folders = [os.path.join(THEMES_FOLDER, theme) for theme in os.listdir(THEMES_FOLDER) if os.path.isdir(os.path.join(THEMES_FOLDER, theme))]
    sorted_theme_folders = sort_folders_by_publish_date(theme_folders)
    
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
        
        print(f"Rebuilt theme: {theme}")
    print("Rebuilt all themes!")
  
if __name__ == '__main__':
    main()
