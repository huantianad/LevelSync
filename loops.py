import json
import logging
import os
import re
import shutil
import zipfile

import requests

from initial import read_config, log_setup


def get_site(verified_only):
    url = 'https://script.google.com/macros/s/AKfycbzm3I9ENulE7uOmze53cyDuj7Igi7fmGiQ6w045fCRxs_sK3D4/exec'
    r = requests.get(url).json()

    # If verified only is enabled, we want to get rid of all unverified levels from site_urls
    if verified_only:
        r = [x for x in r if x.get('verified')]

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

    for char in r'<>:"/\|?* ':
        name = name.replace(char, '')

    if os.path.exists(f'{path}/{name}'):
        name = rename(name, 1, path)

    r = requests.get(url, stream=True)
    with open(f'{path}/{name}', 'wb') as f:
        for ch in r:
            f.write(ch)
    try:
        # Code to unzip the .rdzip file
        with zipfile.ZipFile(f'{path}/{name}', 'r') as file_zip:
            file_zip.extractall(f'{path}/{name.split(".")[0]}')

        # Remove the old rdzip
        os.remove(f'{path}/{name}')
        os.rename(f'{path}/{name.split(".")[0]}', f'{path}/{name}')
    except zipfile.BadZipFile:
        # python detects that the file isn't a zip file, so we ignore trying to unzip it
        logging.warning(f"{name} isn't an actual level")
    except OSError:
        # python cannot physically unzip the file correctly, not really something we can fix.
        logging.warning(f"{name} has some broken characters or stuff. It will be broken. Please tell a mod to fix")

        # this will delete the attempted unzipped folder, just leaving the rdzip
        shutil.rmtree(f'{path}/{name.split(".")[0]}')

    return name


def loop(config):
    path = config['path']
    verified_only = config.getboolean('verified_only')

    try:
        site_urls = get_site(verified_only)
    except Exception:
        return

    with open(f"{path}/sync.json", "r") as file:
        file_data = json.loads(file.read())

    # Creates lists of new and yeeted levels by comparing site and file.
    new_levels = [x for x in site_urls if x not in file_data.keys()]
    yeet_levels = [x for x in file_data.keys() if x not in site_urls]

    # Move yeeted levels
    for level in yeet_levels:
        try:
            shutil.move(f"{path}/{file_data[level]}", f"{path}/yeeted")
        except Exception:
            # Sometimes a folder with the same name already exists and python doesn't like that
            shutil.rmtree(f"{path}/yeeted/{file_data[level]}")
            shutil.move(f"{path}/{file_data[level]}", f"{path}/yeeted")

    # Downloads new levels and puts url and name in a list.
    new_names = [(x, download(x, path)) for x in new_levels]

    # Update file list
    file_data.update(new_names)
    for level in yeet_levels:
        if not file_data.pop(level, None):
            logging.error("Tried to delete a non-existent level from sync.data")

    if new_levels or yeet_levels:
        with open(f"{path}/sync.json", "w") as file:
            file.write(json.dumps(file_data, indent=4))

    if new_levels:
        logging.info(new_levels)
    else:
        logging.info("No new levels found")

    if yeet_levels:
        logging.info(yeet_levels)
    else:
        logging.info("No yeet levels found")


if __name__ == "__main__":
    log_setup()
    try:
        loop(read_config())
    except Exception as e:
        logging.exception("Something bad happened")
        raise e
