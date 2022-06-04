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
import copy
from datetime import datetime
from packaging.version import parse


__location__ = os.path.dirname(os.path.realpath(__file__))


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
    'install_required_dependencies': True,
    'install_optional_dependencies': False,
    'remove_required_dependencies': True,
    'remove_optional_dependencies': False,
    'ignore_conflicts_dependencies': False,
    'alternative_glibc_directory': False,
    'alternative_glibc_version': False
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


parser = argparse.ArgumentParser(description="Install / Update / Remove mods for Factorio", formatter_class=argparse.RawTextHelpFormatter)

group = parser.add_argument_group('Behavior')
group.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                   help="Print URLs and stuff as they happen.")

group.add_argument('-d', '--dry-run', action='store_true', dest='dry_run',
                   help="Don't download files, just state which mods updates would be downloaded.")

group.add_argument('--downgrade', action='store_true', dest='should_downgrade',
                   help="If no compatible version is found, install / update the last mod version for precedent Factorio version.\n"
                        "(ex: If mod has no Factorio 1.0.0 version, it will install the latest mod version for Factorio 0.18)")

group = parser.add_argument_group('Local configuration (override config.json)')
group.add_argument('-p', '--path-to-factorio', dest='factorio_path',
                   help="Path to your Factorio folder.")

group.add_argument('-u', '--user', dest='username',
                   help="Your Factorio username, from player-data.json.")
group.add_argument('-t', '--token', dest='token',
                   help="Your Factorio token, from player-data.json.")

group = parser.add_argument_group('Mod listing')
group.add_argument('-l', '--list', action='store_true', dest='list_mods',
                   help="List installed mods and return. Ignore other switches.")

group = parser.add_argument_group('Mod installation')
group.add_argument('-i', '--install', dest='mod_name_to_install',
                   help="Install the given mod. See README to easily find the correct mod name.")

group = parser.add_argument_group('Mod update')
group.add_argument('-U', '--update', action='store_true', dest='should_update',
                   help="Enable the update process. By default, all mods are updated. See -e/--update-enabled-only.")

group.add_argument('-e', '--update-enabled-only', action='store_true', dest='enabled_only',
                   help="Will only updates mods 'enabled' in 'mod-list.json'.")

group = parser.add_argument_group('Mod removal')
group.add_argument('-r', '--remove', dest='remove_mod_name',
                   help="Remove specified mod.")

group = parser.add_argument_group('Mod enabling / disabling')
group.add_argument('-E', '--enable', dest='enable_mods_name', action='append',
                   help="A mod name to enable. Repeat the flag for each mod you want to enable.")

group.add_argument('-D', '--disable', dest='disable_mods_name', action='append',
                   help="A mod name to disable. Repeat the flag for each mod you want to disable.")

group = parser.add_argument_group('Service reloading (override config.json)')
group.add_argument('--reload', action='store_true', dest='should_reload',
                   help="Enable the restarting of Factorio if any mods are installed / updated. If set, service-name must be set.")

group.add_argument('-s', '--service-name', dest='service_name',
                   help="The service name used to launch Factorio. Do not pass anything if not the case (prevent reloading).")

group = parser.add_argument_group('Dependencies management (override config.json)')
group.add_argument('-nrd', '--no-required-dependencies', action='store_true', dest='disable_required_dependencies',
                   help="Disable the auto-installation of REQUIRED dependencies.")

group.add_argument('-nrrd', '--no-remove-required-dependencies', action='store_false', dest='remove_required_dependencies',
                   help="Enable the removal of all the REQUIRED dependencies of the mod asked to be removed.")

group.add_argument('-iod', '--install-optional-dependencies', action='store_true', dest='install_optional_dependencies',
                   help="Enable the auto-installation of OPTIONAL dependencies.")

group.add_argument('-rod', '--remove-optional-dependencies', action='store_true', dest='remove_optional_dependencies',
                   help="Enable the removal of all the OPTIONAL dependencies of the mod asked to be removed.")

group.add_argument('-icd', '--ignore-conflicts-dependencies', action='store_true', dest='ignore_conflicts_dependencies',
                   help="Ignore any conflicts between mods.")

group = parser.add_argument_group('Alternative GLIBC options (override config.json)')
group.add_argument('--alternative-glibc-directory', dest='alt_glibc_dir',
                   help="Path to the root directory of the alternative GLIBC library.")

group.add_argument('--alternative-glibc-version', dest='alt_glibc_version',
                   help="Version of the alternative GLIBC library.")

group = parser.add_argument_group('Self Updating')
group.add_argument('--update-mod-manager', action='store_true', dest='update_mod_manager',
                   help="Update Factorio-mod-manager. Require GIT. Program will exit after, this flag should be used alone.")


def find_version():
    binary_path = os.path.join(glob['factorio_path'], 'bin/x64/factorio')

    cmd = []
    if glob['alternative_glibc_directory'] is not False and glob['alternative_glibc_version'] is not False:
        cmd.extend((
            "%s/lib/ld-%s.so" % (glob['alternative_glibc_directory'], glob['alternative_glibc_version']),
            "--library-path",
            "%s/lib" % glob['alternative_glibc_directory'],
            binary_path,
            "--executable-path"
        ))

    cmd.extend((binary_path, '--version'))
    version_output = subprocess.check_output(cmd, universal_newlines=True)
    # version_output = subprocess.check_output([binary_path, "--version"], universal_newlines=True)
    # We only capture the MAIN and MAJOR version because from a mod pov the minor version should never be specified
    # see : https://wiki.factorio.com/Tutorial:Mod_structure#info.json -> "factorio_version"
    # "Adding a minor version, e.g. "0.18.27" will make the mod portal reject the mod and the game act weirdly"
    source_version = re.search("Version: (\d+\.\d+)\.\d+ \(build \d+", version_output)
    if source_version:
        main_version = parse(source_version.group(1))
        debug("Auto-detected Factorio version %s from binary." % main_version)
        return main_version


glob_mod_list = []


def read_mods_list(remove_base=True):
    debug('Parsing "mod-list.json"...')
    global glob_mod_list

    if not glob_mod_list:
        try:
            with open(glob['mods_list_path'], 'r') as fd:
                json_decoded = json.load(fd)
                if 'mods' not in json_decoded:
                    print('Error while reading the "mod-list.json" file in %s, there is no mods in it (no "mods" key) !' % glob['mods_list_path'])
                    exit(1)
                glob_mod_list = json_decoded['mods']
        except json.JSONDecodeError:
            print('Error while reading the "mod-list.json" file in %s, it cannot be parsed to Json !' % glob['mods_list_path'])
            exit(1)

    # Remove the 'base' mod
    installed_mods_list = copy.deepcopy(glob_mod_list)
    if remove_base:
        installed_mods_list[:] = [d for d in glob_mod_list if d.get('name') != 'base']

    return installed_mods_list


def add_to_glob_mod_list(new_mod):
    global glob_mod_list
    read_mods_list(False)

    mod_found = False
    for mod in glob_mod_list:
        if mod['name'] == new_mod['name']:
            mod['enabled'] = new_mod['enabled']
            mod_found = True
            break

    if not mod_found:
        glob_mod_list.append(new_mod)


def remove_to_glob_mod_list(mod_to_remove):
    global glob_mod_list
    read_mods_list(False)

    glob_mod_list[:] = [d for d in glob_mod_list if d.get('name') != mod_to_remove['name']]


def write_mods_list():
    debug('Writing to mod-list.json')
    global glob_mod_list
    mods_list_json = {
        "mods": glob_mod_list
    }
    if glob['dry_run']:
        print('Dry-running, would have writen this mods list : %s' % json.dumps(mods_list_json, indent=2))
        return

    with open(glob['mods_list_path'], 'w') as fd:
        json.dump(mods_list_json, fd, indent=2)


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
        return False

    json_result = r.json()

    if 'releases' not in json_result or len(json_result['releases']) == 0:
        debug('Mod "%s" does not seems to have any release ! Skipping...' % (mod['name']))
        return False

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
            return False

    mods_infos = {
        'name': mod['name'],
        'enabled': mod['enabled'],
        'releases': sorted_releases,
        'same_version_releases': filtered_releases
    }

    return mods_infos


# Dependencies rules :
#   "no prefix" = required (must be installed)
#   "~"         = required but does not affect load order (must be installed)
#   "?"         = optional (can be installed)
#   "(?)"       = hidden optional, used to change load order (should not be installed)
#   "!"         = conflict (must NOT be installed)
#   "(!)"       = conflict, should not exist, but I swear I saw it one time (must NOT be installed)
def parse_dependencies(dependencies):
    filtered_dependencies = {"required": [], "optional": [], "conflict": []}

    for mod in dependencies:
        # We clean the mod name
        mod = "".join(mod.split())
        # Split the version comparator. TODO : capture the comparator for later use
        mod = re.split('<|<=|=|>=|>', mod)

        if len(mod) == 1:
            mod.append('latest')

        # Skip "base", "!", "(!)", "?", "(?)"
        if mod[0].find('base') == -1 and not mod[0].startswith(('!', '(!)', '?', '(?)')):
            # TODO future : Split the name and version requirement
            if mod[0].startswith('~'):
                # Remove the first char : "~"
                mod[0] = mod[0][1:]
            filtered_dependencies['required'].append(mod)

        # we ignore dependencies starting with "(?)" as they are hidden optional
        # listed only for load order
        elif mod[0].startswith('?'):
            # Remove the first char : "?"
            mod[0] = mod[0][1:]
            # Split the name and version requirement
            filtered_dependencies['optional'].append(mod)

        # the case "(!)" should not exists but hey, we saw weird things from the API...
        elif mod[0].startswith('!') or mod[0].startswith('(!)'):
            # Remove the first char "!" or "(!)"
            mod[0] = mod[0][1:] if mod[0].startswith('!') else mod[0][3:]

            filtered_dependencies['conflict'].append(mod)

    return filtered_dependencies


def mod_has_conflicts(conflict_list):
    # For each mod already installed
    for mod in read_mods_list():
        # We check if this mod is not in the conflict list of the
        # mod we currently try to install
        if mod['name'] in conflict_list:
            return mod['name']

    return False


def check_file_and_sha(file_path, sha1):
    # We assume that a file with the same name and SHA1 is up-to-date
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

        # Save globally that a reload of Factorio is needed in the end.
        glob['has_to_reload'] = True


glob_install_mod_seen = {}


def install_mod(mod_name, min_mod_version='latest', install_optional_dependencies=True):
    debug('Installing mod %s' % mod_name)
    global glob_install_mod_seen

    if mod_name in glob_install_mod_seen:
        print('Mod "%s" already seen, skipping...' % mod_name)
        return

    glob_install_mod_seen[mod_name] = True

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
    dependencies = parse_dependencies(target_release['info_json']['dependencies'])
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
    if glob['install_required_dependencies'] is True:
        install_dependencies(mod_name, dependencies, "required")

    # Check for optional dependencies if needed
    if install_optional_dependencies is True and glob['install_optional_dependencies'] is True:
        install_dependencies(mod_name, dependencies, "optional")

    # Add the mod to the global list of mods which will be written to "mod-list.json" later
    add_to_glob_mod_list(mod)

    # Check if file already exists and have the same sha1
    file_path = os.path.join(glob['mods_folder_path'], target_release['file_name'])
    if check_file_and_sha(file_path, target_release['sha1']):
        return

    # Download the file
    debug('Downloading mod %s' % (mod_infos['name']))
    file_path = os.path.join(glob['mods_folder_path'], target_release['file_name'])
    download_mod(file_path, target_release['download_url'])

    print('Installed mod %s version %s for Factorio version %s' % (
        mod_name,
        target_release['version'],
        target_release['info_json']['factorio_version']
    ))

    # Save globally that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True

    return True


def install_dependencies(parent_name, dependencies, dependencies_type):
    # Install required / optional dependencies
    for dependency in dependencies[dependencies_type]:
        print('Installing %s dependency "%s" version >= "%s" for "%s"' % (
            dependencies_type,
            dependency[0],
            dependency[1],
            parent_name
        ))
        # Install the dependency and set the flag for optional dependencies (of the dependency) to False
        # Optional dependencies of a dependency should be installed by doing 'mod_manager.py -i $mod_name$ -iod'
        # where $mod_name$ is name of the optional dependency
        install_mod(dependency[0], dependency[1], False)


glob_remove_mod_seen = {}


def remove_mod(mod_name, remove_optional_dependencies=True):
    print('Removing "%s"' % mod_name)
    global glob_remove_mod_seen

    if mod_name in glob_remove_mod_seen:
        print('Mod %s already removed, skipping...' % mod_name)
        return

    glob_remove_mod_seen[mod_name] = True

    mod = {
        'name': mod_name,
        'enabled': True
    }

    mod_infos = get_mod_infos(mod)
    if not mod_infos or len(mod_infos['same_version_releases']) == 0:
        print('No matching version found for the mod "%s". Skipping...' % (mod['name']))
        return False

    # Filter the one release we'll use
    target_release = mod_infos['same_version_releases'][0]

    if glob['remove_required_dependencies'] is True or \
            (glob['remove_optional_dependencies'] is True and remove_optional_dependencies is True):

        dependencies = parse_dependencies(target_release['info_json']['dependencies'])
        if glob['remove_required_dependencies'] is True:
            remove_dependencies(mod_name, dependencies, "required")

        # Check for optional dependencies if needed
        if remove_optional_dependencies is True and glob['remove_optional_dependencies'] is True:
            remove_dependencies(mod_name, dependencies, "optional")

    if mod_infos is not None and 'releases' in mod_infos:
        for release in mod_infos['releases']:
            file_path = os.path.join(glob['mods_folder_path'], release['file_name'])
            remove_file(file_path)
    else:
        debug('No releases found for the mod "%s" skipping...' % mod_name)
        return False

    # We remove the mod from the global list of installed mods,
    # 'mod-list.json' file will be written later
    remove_to_glob_mod_list(mod)

    # Save globally that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True


def remove_dependencies(parent_name, dependencies, dependencies_type):
    # Remove required / optional dependencies
    for dependency in dependencies[dependencies_type]:
        print('Removing "%s", %s dependency of "%s"' % (
            dependency[0],
            dependencies_type,
            parent_name
        ))
        # Remove the dependency but NOT its own optional dependencies.
        # Optional dependencies of a dependency should be removed by doing 'mod_manager.py -r $mod_name$ -rod'
        # where $mod_name$ is name of the optional dependency
        remove_mod(dependency[0], False)


def download_mod(file_path, download_url):
    if glob['dry_run']:
        print('Dry-running, would have downloaded (hiding credentials) : %s' % ('https://mods.factorio.com' + download_url))
        return

    payload = {'username': glob['username'], 'token': glob['token']}
    r = requests.get('https://mods.factorio.com' + download_url, params=payload, stream=True)

    # the Factorio mod portal may serve downloads via a CDN, which 
    # returns 'application/octet-stream' as the Content-Type
    if r.headers.get('Content-Type') != 'application/zip' and r.headers.get('Content-Type') != 'application/octet-stream':
        print('Error : Response is not a Zip file !')
        print('It might happen because your Username and/or Token are wrong or deactivated.')
        print('Aborting the mission...')
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

    for mod in mods_name_list:
        mod_list = {
            'name': mod,
            'enabled': should_enable
        }
        add_to_glob_mod_list(mod_list)

    # Save globally that a reload of Factorio is needed in the end.
    glob['has_to_reload'] = True


def load_config(args):
    debug('Loading configuration...')
    try:
        with open(os.path.join(__location__, 'config.json'), 'r') as fd:
            config = json.load(fd)
    except FileNotFoundError:
        print("Couldn't load config file, as it didn't exist. Continuing with defaults anyway.")
        config = {}

    # GLIBC related
    glob['alternative_glibc_directory'] = args.alt_glibc_dir if args.alt_glibc_dir \
        else (config['alternative_glibc_directory'] if "alternative_glibc_directory" in config else glob['alternative_glibc_directory'])
    glob['alternative_glibc_version'] = args.alt_glibc_version if args.alt_glibc_version \
        else (config['alternative_glibc_version'] if "alternative_glibc_version" in config else glob['alternative_glibc_version'])

    if glob['alternative_glibc_directory'] is not False:
        # We check that if either of glibc params is set, the other is too.
        if (glob['alternative_glibc_directory'] is None and glob['alternative_glibc_version'] is not None) \
                or (glob['alternative_glibc_directory'] is not None and glob['alternative_glibc_version'] is None):
            parser.error(
                'The directory and version parameters for GLIBC must both have a value or not be specified at all. Got :\n'
                'alternative-glibc-directory : %s\n'
                'alternative-glibc-version : %s'
                % (glob['alternative_glibc_directory'], glob['alternative_glibc_version'])
            )
        if glob['alternative_glibc_directory'] is not None and not os.path.isdir(glob['alternative_glibc_directory']):
            parser.error('The directory "%s" for the alternative GLIBC library points to nothing !' % glob['alternative_glibc_directory'])

        glibc_lib_file = "%s/lib/ld-%s.so" % (glob['alternative_glibc_directory'], glob['alternative_glibc_version'])
        if glob['alternative_glibc_directory'] is not None and not os.path.isfile(glibc_lib_file):
            parser.error(
                'Could not find the GLIBC lib file corresponding to version %s ! The file "%s" must exists.' %
                (glob['alternative_glibc_version'], glibc_lib_file)
            )

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

    glob['remove_required_dependencies'] = False if args.remove_required_dependencies is False \
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
    print('Checking for updates...')
    # Python 2 compatibility to silence the call
    try:
        with open(os.devnull, 'wb') as shutup:
            return_code = subprocess.call(["git", "pull", "--quiet", "--ff-only"], cwd=__location__, stdout=shutup, stderr=shutup)

        if return_code != 0:
            print("""
            ###############################################################################################
            An update of Factorio-mod-manager is available but cannot be applied via git-pull ! Ignoring...
            ###############################################################################################
            """)
        else:
            print("No new version found, exiting...")
    except FileNotFoundError:
        print('Cannot find "git" executable, skipping...')


def main():
    if len(sys.argv) == 1:
        parser.print_help()
        exit()

    args = parser.parse_args()

    # Check if an update (of Factorio-mod-manager) is available
    if args.update_mod_manager:
        check_mod_manager_update()
        exit(0)

    if not load_config(args):
        print('Failing miserably...')
        exit(1)

    # List installed mods
    if args.list_mods:
        display_mods_list(read_mods_list())
        exit(0)

    # Enabled mods
    if args.enable_mods_name:
        update_state_mods(args.enable_mods_name, True)
        print()

    # Disabled mods
    if args.disable_mods_name:
        update_state_mods(args.disable_mods_name, False)
        print()

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

    write_mods_list()

    if glob['has_to_reload'] is True:
        print('The mod configuration changed and Factorio need to be restarted in order to apply the changes.')

        if glob['dry_run']:
            print('Dry-running, would have%s automatically reloaded' % (" NOT" if glob['should_reload'] is False else ""))
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
