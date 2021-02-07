#!/usr/bin/env python

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
from packaging.version import parse

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Fix for python 2 FileNotFoundError
try:
    FileNotFoundError
except NameError:
    # noinspection PyShadowingBuiltins
    FileNotFoundError = IOError

# Global parameters with default values
glob = {
    'verbose': False,
    'dry_run': False,
    'factorio_path': None,
    'factorio_version': None,
    'mods_folder_path': None,
    'mods_list_path': None,
    'username': None,
    'token': None,
    'should_reload': False,
    'service_name': None,
    'has_to_reload': None,
    'should_downgrade': False,
    'disable_mod_manager_update': False,
    'install_required_dependencies': True,
    'install_optional_dependencies': False,
    'remove_required_dependencies': False,
    'remove_optional_dependencies': False,
    'ignore_conflicts_dependencies': False
}


# Global, utility functions
def get_file_sha1(file_name):
    blocksize = 65536
    hasher = hashlib.sha1()
    with open(file_name, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()


parser = argparse.ArgumentParser(description="Install / Update / Remove mods for Factorio")

parser.add_argument('-p', '--path-to-factorio', dest='factorio_path',
                    help="Path to your Factorio folder.")

parser.add_argument('-u', '--user', dest='username',
                    help="Your Factorio username, from player-data.json.")
parser.add_argument('-t', '--token', dest='token',
                    help="Your Factorio token, from player-data.json.")

parser.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                    help="Don't download files, just state which mods updates would be downloaded.")

parser.add_argument('-i', '--install', dest='mod_name_to_install',
                    help="Install the given mod. See README to easily find the correct mod name.")

parser.add_argument('-U', '--update', action='store_true', dest='should_update',
                    help="Enable the update process. By default, all mods are updated. Seed -e/--update-enabled-only.")
parser.add_argument('-e', '--update-enabled-only', action='store_true', dest='enabled_only',
                    help="Will only updates mods 'enabled' in 'mod-list.json'.")

parser.add_argument('-l', '--list', action='store_true', dest='list_mods',
                    help="List installed mods and return. Ignore other switches.")

parser.add_argument('-r', '--remove', dest='remove_mod_name',
                    help="Remove specified mod.")

parser.add_argument('-E', '--enable', dest='enable_mods_name', action='append',
                    help="A mod name to enable. Repeat the flag for each mod you want to enable.")
parser.add_argument('-D', '--disable', dest='disable_mods_name', action='append',
                    help="A mod name to disable. Repeat the flag for each mod you want to disable.")

parser.add_argument('--downgrade', action='store_true', dest='should_downgrade',
                    help="If no compatible version is found, install / update the last mod version for precedent Factorio version."
                         "(ex: If mod has no Factorio 1.0.0 version, it will install the latest mod version for Factorio 0.18)")

parser.add_argument('--reload', action='store_true', dest='should_reload',
                    help="Enable the restarting of Factorio if any mods are installed / updated. If set, service-name must be set.")

parser.add_argument('-s', '--service-name', dest='service_name',
                    help="The service name used to launch Factorio. Do not pass anything if not the case (prevent reloading).")

parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help="Print URLs and stuff as they happen.")

parser.add_argument('-nmmu', '--no-mod-manager-update', action='store_true', dest='disable_mod_manager_update',
                    help="Disable the checking of Factorio-mod-manager updates. "
                         "Please disable it ONLY if you encounter errors with this feature (eg: you don't have git installed).")

parser.add_argument('-nrd', '--no-required-dependencies', action='store_true', dest='disable_required_dependencies',
                    help="Disable the auto-installation of REQUIRED dependencies.")

parser.add_argument('-iod', '--install-optional-dependencies', action='store_true', dest='install_optional_dependencies',
                    help="Enable the auto-installation of OPTIONAL dependencies.")

parser.add_argument('-rrd', '--remove-required-dependencies', action='store_true', dest='remove_required_dependencies',
                    help="Enable the removal of all the REQUIRED dependencies of the mod asked to be removed.")

parser.add_argument('-rod', '--remove-optional-dependencies', action='store_true', dest='remove_optional_dependencies',
                    help="Enable the removal of all the OPTIONAL dependencies of the mod asked to be removed.")

parser.add_argument('-icd', '--ignore-conflicts-dependencies', action='store_true', dest='ignore_conflicts_dependencies',
                    help="Ignore any conflicts between mods.")


def find_version():
    binary_path = os.path.join(glob['factorio_path'], 'bin/x64/factorio')
    version_output = subprocess.check_output([binary_path, "--version"], universal_newlines=True)
    # We only capture the MAIN and MAJOR version because from a mod pov the minor version should never be specified
    # see : https://wiki.factorio.com/Tutorial:Mod_structure#info.json -> "factorio_version"
    # "Adding a minor version, e.g. "0.18.27" will make the mod portal reject the mod and the game act weirdly"
    source_version = re.search("Version: (\d+\.\d+)\.\d+ \(build \d+", version_output)
    if source_version:
        main_version = parse(source_version.group(1))
        debug("Auto-detected Factorio version %s from binary." % main_version)
        return main_version


def read_mods_list(remove_base=True):
    debug('Parsing "mod-list.json"...')
    with open(glob['mods_list_path'], 'r') as fd:
        mods_list_dict = json.load(fd)['mods']
    # Remove the 'base' mod
    if remove_base:
        mods_list_dict.pop(0)

    return mods_list_dict


def write_mods_list(mods_list):
    debug('Writing to mod-list.json')
    mods_list_json = {
        "mods": mods_list
    }
    if glob['dry_run']:
        print('Dry-running, would have writed this mods list : %s' % mods_list_json)
        return

    with open(glob['mods_list_path'], 'w') as fd:
        json.dump(mods_list_json, fd, indent=4)


def remove_file(file_path):
    if os.path.isfile(file_path):
        if glob['dry_run']:
            print('Dry-running, would have deleted this file if it exists : %s' % file_path)
            return

        os.remove(file_path)


def display_mods_list(mods_list):
    if len(mods_list) == 0:
        print('No mods are installed')
        return

    print('Currently installed mods :')
    for mod in mods_list:
        print("""    Mod name : %s
    Enabled  : %s
""" % (mod['name'], mod['enabled']))


def get_mod_infos(mod, min_mod_version='latest'):
    debug('Getting mod "%s" infos...' % (mod['name']))
    request_url = 'https://mods.factorio.com/api/mods/' + mod['name'] + '/full'

    r = requests.get(request_url)
    if r.status_code != 200:
        print('Error getting mod "' + mod['name'] + '" infos. Ignoring this mod, please, check your "mod-list.json" file.')
        return

    json_result = r.json()

    if 'releases' not in json_result or len(json_result['releases']) == 0:
        debug('Mod "%s" does not seems to have any release ! Skipping...' % (mod['name']))
        return

    sorted_releases = sorted(json_result['releases'], key=lambda i: datetime.strptime(i['released_at'], '%Y-%m-%dT%H:%M:%S.%fZ'), reverse=True)

    if min_mod_version == 'latest':
        if glob['should_downgrade'] is True:
            filtered_releases = [release for release in sorted_releases if parse(release['info_json']['factorio_version']) <= glob['factorio_version']]
        else:
            filtered_releases = [release for release in sorted_releases if parse(release['info_json']['factorio_version']) == glob['factorio_version']]

    else:
        filtered_releases = [release for release in sorted_releases if parse(release['version']) >= parse(min_mod_version)]

        if len(filtered_releases) == 0:
            print('Asked for mod "%s" at least version "%s" but no result found ! Skipping...' % (
                mod['name'],
                min_mod_version
            ))
            return

    mods_infos = {
        'name': mod['name'],
        'enabled': mod['enabled'],
        'releases': sorted_releases,
        'same_version_releases': filtered_releases
    }

    return mods_infos


def parse_dependencies(release):
    dependencies = {"required": [], "optional": [], "conflict": []}
    for mod in release['info_json']['dependencies']:
        # We clean the the mod name
        mod = "".join(mod.split())

        # Skip the "base" mod
        # Skip mod name starting with "!" (conflict)
        # Skip mod name starting with "?" (optional)
        # Skip mod name not containing a version constraint (malformed api side ?..)
        if not mod.startswith('base') and not mod.startswith('!') and not mod.startswith('?') and ">=" in mod:
            # Split the name and version requirement
            version = mod.split('>=')
            dependencies['required'].append(version)
        else:

            if mod.startswith('?') and ">=" in mod:
                # Remove the first char (?)
                mod = mod[1:]
                # Split the name and version requirement
                version = mod.split(">=")
                dependencies['optional'].append(version)

            if mod.startswith('!'):
                # Remove the first char (!)
                mod = mod[1:]
                dependencies['conflict'].append(mod)

    return dependencies


def mod_has_conflicts(conflict_list):
    # For each mod already installed
    for mod in read_mods_list():
        # We check if this mod is not in the conflict list of the
        # mod we currently try to install
        if mod['name'] in conflict_list:
            return mod['name']

    return False


def check_file_and_sha(file_path, sha1):
    # We assume that a file with the same name and SHA1 is up to date
    if os.path.exists(file_path) and sha1 == get_file_sha1(file_path):
        print('A file already exists at the path "%s" and is identical (same SHA1), skipping...' % file_path)
        return True

    return False


def update_mods(enabled_only):
    debug('Starting mods update...')

    mods_list = read_mods_list()

    for mod in mods_list:
        mod_infos = get_mod_infos(mod)

        if enabled_only and mod_infos['enabled'] is False:
            debug('Mod %s is disable and --update-enabled-only has been used. Skipping...' % (mod_infos['name']))
            continue

        if len(mod_infos['same_version_releases']) == 0:
            print('No matching version found for the mod "%s". Skipping...' % (mod['name']))
            continue

        delete_list = [release for release in mod_infos['releases'] if release['file_name'] not in [mod_infos['same_version_releases'][0]['file_name']]]
        for release in delete_list:
            file_path = os.path.join(glob['mods_folder_path'], release['file_name'])
            debug('Removing old release file : %s' % file_path)
            remove_file(file_path)

        file_path = os.path.join(glob['mods_folder_path'], mod_infos['same_version_releases'][0]['file_name'])
        if check_file_and_sha(file_path, mod_infos['same_version_releases'][0]['sha1']):
            continue

        debug('Downloading mod %s' % (mod_infos['name']))
        download_mod(file_path, mod_infos['same_version_releases'][0]['download_url'])

        # Save globaly that a reload of Factorio is needed in the end.
        glob['has_to_reload'] = True


def install_mod(mod_name, min_mod_version='latest', install_optional_dependencies=True):
    debug('Installing mod %s' % mod_name)

    mod = {
        'name': mod_name,
        'enabled': True
    }
    mod_infos = get_mod_infos(mod, min_mod_version)
    if not mod_infos:
        debug('Mod "%s" not found ! Skipping installation.' % mod_name)
        return

    if len(mod_infos['same_version_releases']) == 0:
        print('No matching version found for the mod "%s". No mod has been installed !' % (mod['name']))
        return

    # Filter the one release we'll use
    target_release = mod_infos['same_version_releases'][0]

    # Check for dependencies if needed
    dependencies = parse_dependencies(target_release)
    # Check for conflicts
    conflict = mod_has_conflicts(dependencies['conflict'])
    if conflict is not False:
        print('Mod "%s" has a conflict with the mod "%s" already installed' % (mod_name, conflict))
        if glob['ignore_conflicts_dependencies'] is True:
            print('Ignoring...')
        else:
            print('Stopping here !')
            exit(0)

    # Install required / optional dependencies
    if glob['install_required_dependencies'] is True or glob['install_optional_dependencies'] is True:
        if glob['install_required_dependencies'] is True:
            for required in dependencies['required']:
                print('Installing dependency "%s" version >= "%s" for "%s"' % (
                    required[0],
                    required[1],
                    mod_name
                ))
                # Install the dependency and set the flag for optional dependencies (of the dependency) to False
                install_mod(required[0], required[1], False)

        # Check for optional dependencies if needed
        if install_optional_dependencies is True and glob['install_optional_dependencies'] is True:
            for optional in dependencies['optional']:
                print('Installing optional dependency "%s" version >= "%s" for "%s"' % (
                    optional[0],
                    optional[1],
                    mod_name
                ))
                # Install the dependency but NOT it's own optional dependencies
                # They should be installed by doing 'mod_manager.py -i $mod_name$ -iod'
                # where $mod_name$ is name of the optional dependency
                install_mod(optional[0], optional[1], False)

    # We add the mod in the 'mod-list.json' file (enabled by default)
    # It may create duplicate to add it here but there's no impact and factorio will clean the
    # 'mod-list.json' file by itself.
    # We do it anyway in case the mod file exists but the 'mod-list.json' file is not up to date.
    mods_list = read_mods_list(False)
    mods_list.append(mod)
    write_mods_list(mods_list)

    # Check if file already exists and have the same sha1
    file_path = os.path.join(glob['mods_folder_path'], target_release['file_name'])
    if check_file_and_sha(file_path, target_release['sha1']):
        return

    # Dowload the file
    debug('Downloading mod %s' % (mod_infos['name']))
    file_path = os.path.join(glob['mods_folder_path'], target_release['file_name'])
    download_mod(file_path, target_release['download_url'])

    print('Installed mod %s version %s for Factorio version %s' % (
        mod_name,
        target_release['version'],
        target_release['info_json']['factorio_version']
    ))

    # Save globaly that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True

    return True


def remove_mod(mod_name, remove_optional_dependencies=True):
    print('Removing mod "%s"' % mod_name)

    mod = {
        'name': mod_name,
        'enabled': True
    }

    mod_infos = get_mod_infos(mod)

    # Filter the one release we'll use
    target_release = mod_infos['same_version_releases'][0]

    if glob['remove_required_dependencies'] is True or glob['remove_optional_dependencies'] is True:
        dependencies = parse_dependencies(target_release)

        if glob['remove_required_dependencies'] is True:
            for required in dependencies['required']:
                print('Removing mod "%s" being a required dependency of "%s"' % (
                    required[0],
                    mod_name
                ))
                # Remove the dependency but NOT it's own optional dependencies.
                remove_mod(required[0], False)

        # Check for optional dependencies if needed
        if remove_optional_dependencies is True and glob['remove_optional_dependencies'] is True:
            for optional in dependencies['optional']:
                print('Removing mod "%s" being a required dependency of "%s"' % (
                    optional[0],
                    mod_name
                ))
                # Remove the dependency but NOT it's own optional dependencies.
                # They should be removed by doing 'mod_manager.py -d $mod_name$ -rod'
                # where $mod_name$ is name of the optional dependency
                remove_mod(optional[0], False)

    if mod_infos is not None and 'releases' in mod_infos:
        releases = mod_infos['releases']
        for mod in releases:
            file_path = os.path.join(glob['mods_folder_path'], mod['file_name'])
            remove_file(file_path)
    else:
        debug('No releases found for the mod "%s" skipping...' % mod_name)
        return False

    # We remove the mod from the 'mod-list.json' file if found
    mods_list = read_mods_list(False)
    new_mods_list = []
    for mod in mods_list:
        if mod_name != mod['name']:
            new_mods_list.append(mod)

    write_mods_list(new_mods_list)

    # Save globaly that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True


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

    # Save globaly that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True


def load_config(args):
    debug('Loading configuration...')
    try:
        with open(os.path.join(__location__, 'config.json'), 'r') as fd:
            config = json.load(fd)
    except FileNotFoundError:
        print("Couldn't load config file, as it didn't exist. Continuing with defaults anyway.")
        config = {}

    # Service related
    glob['should_reload'] = args.should_reload if args.should_reload is True \
        else (config['should_reload'] if "should_reload" in config else glob['should_reload'])
    glob['service_name'] = args.service_name if args.service_name is not None \
        else (config['service_name'] if "service_name" in config else glob['service_name'])

    if glob['should_reload'] is True and glob['service_name'] is None:
        parser.error('Reload of Factorio is enabled but no service name was given. Set it in "config.json" or by passing -s argument.')

    # Path related
    glob['factorio_path'] = os.path.abspath(args.factorio_path) if args.factorio_path is not None \
        else (config['factorio_path'] if "factorio_path" in config else glob['factorio_path'])
    if glob['factorio_path'] is None:
        parser.error('Factorio Path not correctly set. Set it in "config.json" or by passing -p argument.')

    glob['mods_folder_path'] = os.path.join(glob['factorio_path'], 'mods')
    if not os.path.exists(glob['mods_folder_path']) and not os.path.isdir(glob['mods_folder_path']):
        print('Factorio mod folder cannot be found in %s' % (glob['mods_folder_path']))
        return False

    glob['mods_list_path'] = os.path.join(glob['mods_folder_path'], 'mod-list.json')
    if not os.path.exists(glob['mods_list_path']) and not os.path.isfile(glob['mods_list_path']):
        print('Factorio mod list file cannot be found in %s' % (glob['mods_list_path']))
        return False

    # User credential related
    glob['username'] = args.username if args.username is not None \
        else (config['username'] if "username" in config else glob['username'])
    glob['token'] = args.token if args.token is not None \
        else (config['token'] if "token" in config else glob['token'])

    # If we are updating OR there is a mod to install, we ensure that the username and token are set
    if (args.should_update is True or args.mod_name_to_install is not None) and (glob['username'] is None or glob['username'] is None):
        parser.error('Username and/or Token not correctly set. Set them in "config.json" or by passing -u / -t arguments. See README on how to obtain them.')

    # Script configuration related
    glob['disable_mod_manager_update'] = True if args.disable_mod_manager_update is True \
        else (config['disable_mod_manager_update'] if "disable_mod_manager_update" in config else glob['disable_mod_manager_update'])
    glob['verbose'] = args.verbose if args.verbose is not None \
        else (config['verbose'] if "verbose" in config else glob['verbose'])
    glob['dry_run'] = args.dry_run if args.dry_run is not None else glob['dry_run']
    glob['factorio_version'] = find_version()
    glob['should_downgrade'] = args.should_downgrade if args.should_downgrade is not None \
        else (config['should_downgrade'] if "should_downgrade" in config else glob['should_downgrade'])

    # Dependencies related
    glob['install_required_dependencies'] = False if args.disable_required_dependencies is True \
        else (config['install_required_dependencies'] if "install_required_dependencies" in config else glob['install_required_dependencies'])
    glob['install_optional_dependencies'] = True if args.install_optional_dependencies is True \
        else (config['install_optional_dependencies'] if "install_optional_dependencies" in config else glob['install_optional_dependencies'])

    glob['remove_required_dependencies'] = True if args.remove_required_dependencies is True \
        else (config['remove_required_dependencies'] if "remove_required_dependencies" in config else glob['remove_required_dependencies'])
    glob['remove_optional_dependencies'] = True if args.remove_optional_dependencies is True \
        else (config['remove_optional_dependencies'] if "remove_optional_dependencies" in config else glob['remove_optional_dependencies'])

    glob['ignore_conflicts_dependencies'] = True if args.ignore_conflicts_dependencies is True \
        else (config['ignore_conflicts_dependencies'] if "ignore_conflicts_dependencies" in config else glob['ignore_conflicts_dependencies'])

    return True


def debug(string):
    if glob['verbose'] is True:
        print('Debug: ' + string, end='\n\n')


def check_mod_manager_update():
    try:
        cwd = os.path.dirname(os.path.abspath(__file__))
        # Update the remote status
        subprocess.check_output(["git", "remote", "update"], cwd=cwd)
        # Get the hash of the last local commit
        local = subprocess.check_output(["git", "rev-parse", "@{0}"], cwd=cwd)
        # Get the hash of the last commit on the remote
        remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=cwd)

        if local != remote:
            print("""
            ############################################################################
            An update of Factorio-mod-manager is available, please update via 'git pull'
            ############################################################################
            """)
    except subprocess.CalledProcessError:
        print("An error occured during the version checking of Factorio-mod-manager, ignoring...")


def main():
    if len(sys.argv) == 1:
        parser.print_help()
        exit()

    args = parser.parse_args()

    if not load_config(args):
        print('Failing miserably...')
        exit(1)

    # Check if an update (of Factorio-mod-manager) is available
    if glob['disable_mod_manager_update'] is False:
        check_mod_manager_update()

    # Enabled mods
    if args.enable_mods_name:
        update_state_mods(args.enable_mods_name, True)
        print()

    # Disabled mods
    if args.disable_mods_name:
        update_state_mods(args.disable_mods_name, False)
        print()

    # List installed mods
    if args.list_mods:
        display_mods_list(read_mods_list())
        exit(0)

    # If we should update the mods
    if args.should_update:
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

    if glob['has_to_reload'] is True:
        print('The mod configuration changed and Factorio need to be restarted in order to apply the changes.')

        if glob['dry_run']:
            print('Dry-running, would have%s automaticaly reloaded' % (" NOT" if glob['should_reload'] is False else ""))
            return

        if glob['should_reload'] is True:
            print('Reloading service %s' % (glob['service_name']))
            os.system('systemctl restart %s' % (glob['service_name']))
        else:
            print('Automatic reload has been disabled, please restart Factorio by yourself.')

    print('Finished !')
    exit(0)


if __name__ == '__main__':
    sys.exit(main())
