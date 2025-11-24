import json

THEMES_DATA_FILE = './themes.json'

def load_themes_data():
    with open(THEMES_DATA_FILE, 'r') as f:
        return json.load(f)

def generate_readme(themes_data):
    with open('README.md', 'w') as readme:
        readme.write('<div id="toc" align="center"><a href="https://github.com/amnweb/yasb"><img src="https://raw.githubusercontent.com/amnweb/yasb/main/src/assets/images/app_icon.png" width="64"></a><ul style="list-style:none"><summary><h2>Theme repository for YASB</h2></summary></ul></div>\n\n')
        readme.write('## Submitting a Theme\n\n')
        readme.write('To submit a theme, please follow these steps:\n')
        readme.write('1. Open an issue in [this template](https://github.com/amnweb/yasb-themes/issues/new?assignees=&labels=new-theme&projects=&template=create-theme.yaml&title=%5Bcreate-theme%5D%3A+) with the title `[create-theme]: <theme-name>`\n')
        readme.write('2. Fill out the template with the necessary information\n')
        readme.write('3. Submit the issue\n')
        readme.write('4. Let us take care of the rest!\n')
        readme.write('## Updating a Theme\n\n')
        readme.write('To update a theme, please follow these steps:\n')
        readme.write('1. Create a new pull request with the updated theme.\n')
        readme.write('2. Make sure to include the theme name in the title.\n')
        readme.write('3. Submit the pull request.\n')
        readme.write('4. Let us take care of the rest!.\n')
        readme.write('> This applied to any other actions you want to take with the themes in this repository, such as deleting a theme.\n\n')
        readme.write('## Latest Themes\n')
        for theme_id, theme_data in themes_data.items():
            name = theme_data['name']
            image = theme_data['image']
            readme.write(f'## [{name}](themes/{theme_id})\n\n')
            readme.write(f'<a title="{name} YASB Theme" href="themes/{theme_id}"><img src="{image}" width="830px"></a>\n\n')
            readme.write('\n')

if __name__ == "__main__":
    themes_data = load_themes_data()
    generate_readme(themes_data)
