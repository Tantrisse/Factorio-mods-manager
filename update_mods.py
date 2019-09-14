#!/usr/bin/env python2

from __future__ import print_function
import os, requests, sys, json, hashlib, argparse
from datetime import datetime

glob = {'verbose': False, 'dry_run': False}

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

def file_path(string):
    if os.path.isfile(string):
        return string
    else:
        raise Exception(string + " is not a valid path to a file.")

parser = argparse.ArgumentParser(description="Fetches Factorio mods update (from mod_list.json)")
parser.add_argument('-p', '--mod-list-path', type=file_path, dest='mod_list_path', required=True,
                    help="Oui.")
parser.add_argument('-u', '--user', dest='username', required=True,
                    help="Your Factorio service username, from player-data.json.")
parser.add_argument('-t', '--token', dest='token', required=True,
                    help="Your Factorio service token, also from player-data.json.")
parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which mods updates would be downloaded.")
parser.add_argument('-i', '--install', dest='mod_name_to_install',
                    help="Install the mod. See README on how to easily get the correct name for the mod.")
parser.add_argument('-e', '--update-enabled-only', action='store_true', dest='enabled_only',
                    help="Will only updates mods 'enabled' in 'mod_list.json'.")
parser.add_argument('-n', '--no-update', action='store_true', dest='dont_update',
                    help="Disabled the update process. Usefull if you just want to install a mod and you are sure other mods are up to date.")
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")

def read_mods_list(mods_list_path):
    print('Parsing "mod_list.json"...')
    with open(mods_list_path, 'r') as f:
        mods_list_dict = json.load(f)['mods']
    # Remove the 'base' mod
    mods_list_dict.pop(0)

    return mods_list_dict


def get_last_mods_version(mods_list, enabled_only):
    print('Getting mod infos...')

    filtered_mods_list = []
    for mod in mods_list:
        mod_name = mod['name']

        if enabled_only and mod['enabled'] is False:
            print('Mod %s is disable and --update-enabled-only has been used. Skipping...' % (mod_name))
            continue

        request_url = 'https://mods.factorio.com/api/mods/' + mod_name

        r = requests.get(request_url)
        if r.status_code != 200:
            print('Error getting mod "' + mod_name + '" infos. Ignoring this mod, please, check your "mod_list.json" file.')
            continue

        if 'releases' not in r.json():
            print('Reponse from the server for the mod "%s" seems incorrect ! Skipping...' % (mod_name))

        releases = r.json()['releases']
        sorted_releases = sorted(releases, key = lambda i: datetime.strptime(i['released_at'], '%Y-%m-%dT%H:%M:%S.%fZ'), reverse=True)

        if len(sorted_releases) == 0:
            print('Mod "%s" does not seems to have any release ! Skipping...' % (mod_name))

        mods_infos = {
            'name': mod['name'],
            'enabled': mod['enabled'],
            'last_release': sorted_releases[0]
        }
        filtered_mods_list.append(mods_infos)

    return filtered_mods_list


def update_mods(mods_folder, mods_list, username, token):
    print('Downloading mods update...')

    for mod in mods_list:
        file_path = os.path.join(mods_folder, mod['last_release']['file_name'])

        # We assume that a file with the same name and SHA1 is up to date
        if os.path.exists(file_path) and mod['last_release']['sha1'] == get_file_sha1(file_path):
            print('A file already exists for the mod "%s" and is identical (same SHA1), skipping...' % (mod['name']))
            continue

        print('Downloading mod %s' % (mod['name']))
        download_mod(file_path, mod['last_release']['download_url'], username, token)


def install_mod(mods_folder, mod_name):
    print('Installing mod %s' % (mod_name))

    mod = [{
        'name': mod_name,
        'enabled': True
    }]
    mod_infos = get_last_mods_version(mod)
    if len(mod_infos) == 0:
        print('Mod "%s" not found ! Skipping installation.' % (mod_name))

    if glob['dry_run']:
        print('Dry-running, mod not installed.')
        return

    file_path = os.path.join(mods_folder, mod_infos[0]['last_release']['file_name'])
    download_mod(file_path, mod_infos[0]['last_release']['download_url'])


def download_mod(file_path, download_url, username, token):
    if glob['dry_run']:
        print('Dry-running, mod have an update pending.')
        return

    payload = {'username': username, 'token': token}
    r = requests.get('https://mods.factorio.com' + download_url, params=payload, stream=True)

    with open(file_path, 'wb') as fd:
        total_length = r.headers.get('content-length')
        if total_length is None: # no content length header
            fd.write(r.content)
        else:
            dl = 0
            total_length = int(total_length)
            for chunk in r.iter_content(8192):
                dl += len(chunk)
                fd.write(chunk)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )
                sys.stdout.flush()
    print('\n')

def main():
    args = parser.parse_args()
    glob['verbose'] = args.verbose
    glob['dry_run'] = args.dry_run

    mod_folder_path = os.path.dirname(os.path.abspath(args.mod_list_path))

    if args.dont_update is False:
        mods_list = read_mods_list(args.mod_list_path)

        mods_list = get_last_mods_version(mods_list, args.enabled_only)

        update_mods(mod_folder_path, mods_list, args.username, args.token)

    if args.mod_name_to_install:
        install_mod(mod_folder_path, args.mod_name_to_install)

    print('Finished !')
    return 0

if __name__ == '__main__':
    sys.exit(main())
