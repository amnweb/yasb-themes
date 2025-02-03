import os
import argparse
import json
import uuid
import sys
import requests
import urllib.parse

STYLES_FILE = "styles.css"
README_FILE = "readme.md"
IMAGE_FILE = "image.png"
CONFIG_FILE = "config.yaml"

TEMPLATE_STYLES_FILE = "./styles.css"
TEMPLATE_CONFIG_FILE = "./config.yaml"
TEMPLATE_README_FILE = "./readme.md"

def create_theme_id():
    return str(uuid.uuid4())

def get_static_asset(theme_id, asset):
    return f"https://raw.githubusercontent.com/amnweb/yasb-themes/main/themes/{theme_id}/{asset}"

def get_styles():
    with open(TEMPLATE_STYLES_FILE, 'r') as f:
        content = f.read()
        content = content[len("```css"):]
        content = content[:-len("```")]
        return content.lstrip('\n')

def get_config():
    with open(TEMPLATE_CONFIG_FILE, 'r') as f:
        content = f.read()
        content = content[len("```yaml"):]
        content = content[:-len("```")]
        return content.lstrip('\n')
    
def get_readme():
    with open(TEMPLATE_README_FILE, 'r') as f:
        content = f.read()
        content = content[len("```markdown"):]
        content = content[:-len("```")]
        return content.lstrip('\n')
    
def validate_url(url, allow_empty=False):
    if allow_empty and len(url) == 0:
        return
    try:
        result = urllib.parse.urlparse(url)
        if result.scheme != 'https':
            print("URL must be HTTPS.", file=sys.stderr)
            exit(1)
    except Exception as e:
        print("URL is invalid.", file=sys.stderr)
        print(e, file=sys.stderr)
        exit(1)

def validate_name(name):
    if len(name) == 0:
        print("Name is required.", file=sys.stderr)
        exit(1)
    if len(name) > 50:
        print("Name must be less than 50 characters.", file=sys.stderr)
        exit(1)
    for char in name:
        if not char.isalnum() and char != ' ':
            print("Name must only contain letters, numbers, and spaces.", file=sys.stderr)
            exit(1)
  
def validate_description(description):
    if len(description) == 0:
        print("Description is required.", file=sys.stderr)
        exit(1)
    if len(description) > 200:
        print("Description must be less than 200 characters.", file=sys.stderr)
        exit(1)

def download_image(image_url, image_path):
    response = requests.get(image_url, headers={'User-Agent': 'Epicture'})
    if response.status_code != 200:
        print("Image URL is invalid.", file=sys.stderr)
        exit(1)
    # Check if the image is valid and a PNG
    if response.headers['Content-Type'] != 'image/png':
        print("Image must be a PNG.", file=sys.stderr)
        exit(1)
    with open(image_path, 'wb') as f:
        f.write(response.content)

def main():
    parser = argparse.ArgumentParser(description='Submit a theme to the theme repo.')
    parser.add_argument('--name', type=str, help='The theme to submit.')
    parser.add_argument('--description', type=str, help='The description of the theme.')
    parser.add_argument('--homepage', type=str, help='The homepage of the theme.')
    parser.add_argument('--author', type=str, help='The author of the theme.')
    parser.add_argument('--image', type=str, help='The image of the theme.')
    args = parser.parse_args()

    name = args.name
    description = args.description
    homepage = args.homepage
    author = args.author
    image = args.image

    validate_name(name)
    validate_description(description)

    validate_url(image)
    validate_url(homepage, allow_empty=True)

    theme_id = create_theme_id()
 
    theme = {
        'id': theme_id,
        'name': name,
        'description': description,
        'homepage': homepage,
        'style': get_static_asset(theme_id, STYLES_FILE),
        'config': get_static_asset(theme_id, CONFIG_FILE),
        'readme': get_static_asset(theme_id, README_FILE),
        'image': get_static_asset(theme_id, IMAGE_FILE),
        'author': author
    }
    os.makedirs(f"themes/{theme_id}")

    with open(f"themes/{theme_id}/{STYLES_FILE}", 'w') as f:
        f.write(get_styles())

    with open(f"themes/{theme_id}/{CONFIG_FILE}", 'w') as f:
        f.write(get_config())
        
    with open(f"themes/{theme_id}/{README_FILE}", 'w') as f:
        f.write(get_readme())

    download_image(image, f"themes/{theme_id}/{IMAGE_FILE}")
    with open(f"themes/{theme_id}/theme.json", 'w') as f:
        json.dump(theme, f)
    print(f"Theme submitted with ID: {theme_id}")
    for key, value in theme.items():
        print(f"\t{key}: {value}")

if __name__ == '__main__':
    main()
