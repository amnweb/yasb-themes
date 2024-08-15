import os
import subprocess
from datetime import datetime

def list_folders_and_images():
    folders = [f for f in os.listdir('.') if os.path.isdir(f)]
    folder_images = {}
    for folder in folders:
        images = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.bmp', '.jpg', '.jpeg', '.gif', '.webp'))]
        if images:
            folder_images[folder] = images
    return folder_images

def get_last_commit_date(folder):
    try:
        # Get the last commit date for the folder
        result = subprocess.run(['git', 'log', '-1', '--format=%ct', folder], capture_output=True, text=True, check=True)
        timestamp = int(result.stdout.strip())
        return datetime.fromtimestamp(timestamp)
    except subprocess.CalledProcessError:
        return None

def sort_folders_by_commit_date(folder_images):
    folder_commit_dates = {}
    for folder in folder_images.keys():
        commit_date = get_last_commit_date(folder)
        if commit_date:
            folder_commit_dates[folder] = commit_date
        else:
            # If no commit date is found, use a very old date to push it to the end
            folder_commit_dates[folder] = datetime.min
    sorted_folders = sorted(folder_commit_dates.keys(), key=lambda f: folder_commit_dates[f], reverse=True)
    
    return sorted_folders

def generate_readme(folder_images, sorted_folders):
    with open('README.md', 'w') as readme:
        readme.write('YASB Theme\n\n')
        for folder in sorted_folders:
            images = folder_images[folder]
            readme.write(f'## [{folder}]({folder})\n\n')
            for image in images:
                image_path = os.path.join(folder, image)
                readme.write(f'<a title="{folder} YASB Theme" href="{folder}"><img src="{image_path}" width="830px"></a>\n\n')
            readme.write('\n')

if __name__ == "__main__":
    folder_images = list_folders_and_images()
    sorted_folders = sort_folders_by_commit_date(folder_images)
    generate_readme(folder_images, sorted_folders)
