#!/usr/bin/env python2

from __future__ import print_function
import os
import requests
import sys
import json
import hashlib
import argparse
import subprocess
import re
from datetime import datetime

glob = {
    'verbose': False,
    'dry_run': False,
    'factorio_path': None,
    'factorio_version': None,
    'mods_folder_path': None,
    'mods_list_path': None,
    'username': None,
    'token': None
}


# Global, utility functions
def get_file_sha1(file):
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(file, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()


parser = argparse.ArgumentParser(description="Install / Update / Remove mods for Factorio")

parser.add_argument('-p', '--path-to-factorio', dest='factorio_path',
                    help="Path to your factorio folder.")

parser.add_argument('-u', '--user', dest='username',
                    help="Your Factorio service username, from player-data.json.")
parser.add_argument('-t', '--token', dest='token',
                    help="Your Factorio service token, from player-data.json.")

parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which mods updates would be downloaded.")

parser.add_argument('-i', '--install', dest='mod_name_to_install',
                    help="Install the given mod. See README to find how easily get the correct name for the mod.")

parser.add_argument('-U', '--update', action='store_true', dest='sould_update',
                    help="Enable the update process. By default, all mods are updated. Seed -e/--update-enabled-only.")
parser.add_argument('-e', '--update-enabled-only', action='store_true', dest='enabled_only',
                    help="Will only updates mods 'enabled' in 'mod-list.json'.")

parser.add_argument('-l', '--list', action='store_true', dest='list_mods',
                    help="List installed mods and return. Ignore other switches.")

parser.add_argument('-r', '--remove', dest='remove_mod_name',
                    help="Remove specified mod.")

parser.add_argument('-E', '--enable-mod', dest='list_enable_mods', action='append',
                    help="A mod name to enable. Repeat the flag for each mod you want to enable.")
parser.add_argument('-D', '--disable-mod', dest='list_disable_mods', action='append',
                    help="A mod name to disable. Repeat the flag for each mod you want to disable.")

parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")


def find_version():
    binary_path = glob['factorio_path'] + '/bin/x64/factorio'
    version_output = subprocess.check_output([binary_path, "--version"], universal_newlines=True)
    source_version = re.search("Version: (\d+\.\d+)\.\d+ \(build \d+", version_output)
    if source_version:
        main_version = source_version.group(1)
        print("Auto-detected factorio version %s from binary." % (main_version))
        return main_version


def read_mods_list(remove_base=True):
    print('Parsing "mod-list.json"...')
    with open(glob['mods_list_path'], 'r') as fd:
        mods_list_dict = json.load(fd)['mods']
    # Remove the 'base' mod
    if remove_base:
        mods_list_dict.pop(0)

    return mods_list_dict


def write_mods_list(mods_list):
    print('Writing to mod-list.json')
    mods_list_json = {
        "mods": mods_list
    }
    with open(glob['mods_list_path'], 'w') as fd:
        json.dump(mods_list_json, fd, indent=4)


def display_mods_list(mods_list):
    print('Currently installed mods :')
    for mod in mods_list:
        print("""    Mod name : %s
    Enabled  : %s
""" % (mod['name'], mod['enabled']))


def get_mod_infos(mod):
    print('Getting mod "%s" infos...' % (mod['name']))
    request_url = 'https://mods.factorio.com/api/mods/' + mod['name']

    r = requests.get(request_url)
    if r.status_code != 200:
        print('Error getting mod "' + mod['name'] + '" infos. Ignoring this mod, please, check your "mod-list.json" file.')
        return

    if 'releases' not in r.json() and len(r.json()['releases']) == 0:
        print('Mod "%s" does not seems to have any release ! Skipping...' % (mod['name']))
        return

    sorted_releases = sorted(r.json()['releases'], key=lambda i: datetime.strptime(i['released_at'], '%Y-%m-%dT%H:%M:%S.%fZ'), reverse=True)
    filtered_releases = [re for re in sorted_releases if re['info_json']['factorio_version'] in [glob['factorio_version']]]

    mods_infos = {
        'name': mod['name'],
        'enabled': mod['enabled'],
        'releases': sorted_releases,
        'same_version_releases': filtered_releases
    }

    return mods_infos


def check_file_and_sha(file_path, sha1):
    # We assume that a file with the same name and SHA1 is up to date
    if os.path.exists(file_path) and sha1 == get_file_sha1(file_path):
        print('A file already exists at the path "%s" and is identical (same SHA1), skipping...' % (file_path))
        return True

    return False


def update_mods(enabled_only):
    print('Starting mods update...')

    mods_list = read_mods_list()

    for mod in mods_list:
        mod_infos = get_mod_infos(mod)

        if enabled_only and mod_infos['enabled'] is False:
            print('Mod %s is disable and --update-enabled-only has been used. Skipping...' % (mod_infos['name']))
            continue

        if len(mod_infos['same_version_releases']) == 0:
            print('No matching version found for the mod "%s". Skipping...' % (mod['name']))
            continue

        delete_list = [re for re in mod_infos['releases'] if re['file_name'] not in [mod_infos['same_version_releases'][0]['file_name']]]
        for release in delete_list:
            file_path = os.path.join(glob['mods_folder_path'], release['file_name'])
            if os.path.isfile(file_path):
                print('Removing old release file : %s' % (file_path))
                os.remove(file_path)

        file_path = os.path.join(glob['mods_folder_path'], mod_infos['same_version_releases'][0]['file_name'])
        if check_file_and_sha(file_path, mod_infos['same_version_releases'][0]['sha1']):
            continue

        print('Downloading mod %s' % (mod_infos['name']))
        download_mod(file_path, mod_infos['same_version_releases'][0]['download_url'])


def install_mod(mod_name):
    print('Installing mod %s' % (mod_name))

    mod = {
        'name': mod_name,
        'enabled': True
    }
    mod_infos = get_mod_infos(mod)
    if not mod_infos:
        print('Mod "%s" not found ! Skipping installation.' % (mod_name))
        return

    if not glob['dry_run']:
        # We add the mod in the 'mod-list.json' file (enabled by default)
        mods_list = read_mods_list(False)
        mods_list.append(mod)
        write_mods_list(mods_list)

    file_path = os.path.join(glob['mods_folder_path'], mod_infos['same_version_releases'][0]['file_name'])
    if check_file_and_sha(file_path, mod_infos['same_version_releases'][0]['sha1']):
        return

    print('Downloading mod %s' % (mod_infos['name']))
    file_path = os.path.join(glob['mods_folder_path'], mod_infos['same_version_releases'][0]['file_name'])
    download_mod(file_path, mod_infos['same_version_releases'][0]['download_url'])

    return True


def remove_mod(mod_name):
    mod = {
        'name': mod_name,
        'enabled': True
    }

    print('Removing mod "%s"' % (mod['name']))

    mod_infos = get_mod_infos(mod)['releases']
    for mod in mod_infos:
        file_path = os.path.join(glob['mods_folder_path'], mod['file_name'])

        if glob['dry_run']:
            print('Dry-running, would have removed : %s ' % (file_path))
            return

        if os.path.isfile(file_path):
            print('Removing file : %s' % (file_path))
            os.remove(file_path)

    # We remove the mod from the 'mod-list.json' file if found
    mods_list = read_mods_list(False)
    new_mods_list = []
    for mod in mods_list:
        if mod['name'] not in ['bobinserters']:
            new_mods_list.append(mod)
    write_mods_list(new_mods_list)


def download_mod(file_path, download_url):
    if glob['dry_run']:
        print('Dry-running, would have downloaded (hiding credentials) : %s' % ('https://mods.factorio.com' + download_url))
        return

    payload = {'username': glob['username'], 'token': glob['token']}
    r = requests.get('https://mods.factorio.com' + download_url, params=payload, stream=True)

    if r.headers.get('Content-Type') != 'application/zip':
        print('Error : Response is not a Zip file !')
        print('It might happen because your Username and/or Token are wrong or deactivated.')
        print('Abording the mission...')
        exit(1)

    with open(file_path, 'wb') as fd:
        total_length = r.headers.get('content-length')
        if total_length is None:  # no content length header
            fd.write(r.content)
        else:
            dl = 0
            total_length = int(total_length)
            for chunk in r.iter_content(8192):
                dl += len(chunk)
                fd.write(chunk)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                sys.stdout.flush()
        print()
    # We ensure all users can read the file (dirty fix case run as root...)
    os.chmod(file_path, 0o644)


def update_state_mods(mods_name_list, should_enable):
    print('%s mod(s) %s' % ('Enabling' if should_enable else 'Disabling', mods_name_list))
    mods_list = read_mods_list(False)
    for mod in mods_list:
        if mod['name'] in mods_name_list:
            mod['enabled'] = should_enable

    write_mods_list(mods_list)


def load_config(args):
    print('Loading configuration...')
    with open('./config.json', 'r') as fd:
        config = json.load(fd)

    glob['factorio_path'] = os.path.abspath(args.factorio_path) if args.factorio_path else (config['factorio_path'] if "factorio_path" in config else False)

    glob['mods_folder_path'] = glob['factorio_path'] + '/mods'
    if not os.path.exists(glob['mods_folder_path']) and not os.path.isdir(glob['mods_folder_path']):
        print('Factorio mod folder cannot be found in %s' % (glob['mods_folder_path']))
        print('Failing miserably...')
        return

    glob['mods_list_path'] = glob['mods_folder_path'] + '/mod-list.json'
    if not os.path.exists(glob['mods_list_path']) and not os.path.isfile(glob['mods_list_path']):
        print('Factorio mod list file cannot be found in %s' % (glob['mods_list_path']))
        print('Failing miserably...')
        return

    glob['username'] = args.username or (config['username'] if "username" in config else "")
    glob['token'] = args.token or (config['token'] if "token" in config else "")
    if glob['username'] == "" or glob['username'] == "":
        print('Username and/or Token not correctly set. Set them in "config.json" or by passing -u / -t arguments. See README on how to obtain them.')
        return

    glob['verbose'] = args.verbose or (config['verbose'] if "verbose" in config else False)
    glob['dry_run'] = args.dry_run
    glob['factorio_version'] = find_version()

    return True


def main():
    if len(sys.argv) == 1:
        parser.print_help()
        exit()

    args = parser.parse_args()

    if not load_config(args):
        exit(1)

    if args.list_enable_mods:
        update_state_mods(args.list_enable_mods, True)
        print()

    if args.list_disable_mods:
        update_state_mods(args.list_disable_mods, False)
        print()

    # List installed mods
    if args.list_mods:
        display_mods_list(read_mods_list())
        exit(0)

    # If we should update the mods
    if args.sould_update:
        # mods_list = get_mods_last_version(read_mods_list(), args.enabled_only)
        update_mods(args.enabled_only)
        print()

    # If there is a mod to install
    if args.mod_name_to_install:
        install_mod(args.mod_name_to_install)
        print()

    # If there is a mod to remove
    if args.remove_mod_name:
        remove_mod(args.remove_mod_name)
        print()

    print('Finished !')
    exit(0)


if __name__ == '__main__':
    sys.exit(main())
