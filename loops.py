import json
import os
import shutil
import zipfile
import re

import requests
import requests_cache


# requests_cache.install_cache('cool_cache')


def get_site():
    url = 'https://script.google.com/macros/s/AKfycbzm3I9ENulE7uOmze53cyDuj7Igi7fmGiQ6w045fCRxs_sK3D4/exec'
    r = json.loads(requests.get(url).content)
    return [x['download_url'] for x in r]


def rename(name, index, path):
    name = name.split('.rdzip')[0]
    if os.path.exists(f'{path}/{name} ({index}).rdzip'):
        return rename(name, index + 1, path)
    else:
        return f"{name} ({index})" + ".rdzip"


def download(url, path):
    if url.startswith('https://drive.google.com/') or url.startswith("https://www.dropbox.com/s/"):
        r = requests.get(url)
        name = re.findall('filename=(.+)', r.headers.get('Content-Disposition'))[0].split(";")[0].replace('"', "")
    else:
        name = url.split('/')[-1]

    if os.path.exists(f'{path}/{name}'):
        name = rename(name, 1, path)

    r = requests.get(url, stream=True)
    with open(f'{path}/{name}', 'wb') as f:
        for ch in r:
            f.write(ch)
    try:
        with zipfile.ZipFile(f'{path}/{name}', 'r') as file_zip:
            file_zip.extractall(f'{path}/{name.split(".")[0]}')
        os.remove(f'{path}/{name}')
        os.rename(f'{path}/{name.split(".")[0]}', f'{path}/{name}')
    except zipfile.BadZipFile:
        print("This level isn't an actual level")

    return name


def loop(path):
    try:
        site_urls = get_site()
    except:
        return

    with open(f"{path}/sync.json", "r") as file:
        file_data = json.loads(file.read())

    # Creates lists of new and yeeted levels by comparing site and file.
    new_levels = [x for x in site_urls if x not in file_data.keys()]
    yeet_levels = [x for x in file_data.keys() if x not in site_urls]

    # Downloads new levels and puts url and name in a list.
    new_names = [(x, download(x, path)) for x in new_levels]

    # Move yeeted levels
    for level in yeet_levels:
        shutil.move(f"{path}/{file_data[level]}", f"{path}/yeeted")

    # Update file list
    file_data.update(new_names)
    for level in yeet_levels:
        if not file_data.pop(level, None):
            print("Tried to delete a non-existent level from sync.data")

    with open(f"{path}/sync.json", "w") as file:
        file.write(json.dumps(file_data, indent=4))

    if new_levels:
        print(new_levels)
    else:
        print("No new levels found")

    if yeet_levels:
        print(yeet_levels)
    else:
        print("No yeet levels found")


if __name__ == "__main__":
    loop(r"C:\Users\david\Documents\Rhythm Doctor\Levels")
