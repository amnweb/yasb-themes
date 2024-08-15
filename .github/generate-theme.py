import os
import re
import requests
import json
import sys

with open('issue_body_raw.json', 'r') as file:
    issue_body = file.read()
cleaned_issue_body = re.sub(r'^```|```$', '', issue_body.strip())

try:
    data = json.loads(cleaned_issue_body)
  
    name = data['name'].replace(' ', '-')
    image_url = data['image']
    style_url = data['style']
    config_url = data['config']
    repository = data['repository']
    description = data['description']

    # Check if any required field is empty
    if not name or not image_url or not style_url or not config_url:
        print("One or more required fields are empty. Stopping job.")
        sys.exit(1)
        
    # Check if the folder already exists
    if os.path.exists(name):
        print(f"Folder '{name}' already exists. Stopping job.")
        sys.exit(1)
 

    # Create directory
    os.makedirs(name, exist_ok=True)

    # Download files
    def download_file(url, path):
        response = requests.get(url)
        with open(path, 'wb') as file:
            file.write(response.content)

    download_file(image_url, f"{name}/image.png")
    download_file(style_url, f"{name}/styles.css")
    if config_url:
        download_file(config_url, f"{name}/config.yaml")

    # Create README file
    with open(f"{name}/README.md", 'w') as readme:
        readme.write(f"# {name}\n\n")
        readme.write("## Image\n")
        readme.write(f"![Image](image.png)\n\n")
        readme.write("## Config\n")
        if config_url:
            with open(f"{name}/config.yaml", 'r') as config_file:
                config_content = config_file.read()
            readme.write("```yaml\n")
            readme.write(config_content)
            readme.write("\n```\n\n")
        readme.write("## Styles\n")
        with open(f"{name}/styles.css", 'r') as style_file:
            style_content = style_file.read()
        readme.write("```css\n")
        readme.write(style_content)
        readme.write("\n```\n")
        if repository:
            readme.write("## Repository URL\n")
            readme.write(f"{repository}\n\n")
        if description:
            readme.write("## Description\n")
            readme.write(f"{description}\n\n")

    # Commit and push changes
    os.system('git config --global user.name "github-actions[bot]"')
    os.system('git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"')
    os.system(f'git add {name}')
    os.system(f'git commit -m "Add files for {name}"')
    os.system('git push')

except Exception as e:
    print(f"Error processing issue: {e}")
    sys.exit(1)
