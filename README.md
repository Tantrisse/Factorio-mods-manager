This is a tool for [Factorio](http://www.factorio.com/) headless server management.
It provides mod management : List / Install / Update / Remove / Enable / Disable.

This package is heavily inspired by [Factorio-mod-updater](https://github.com/astevens/factorio-mod-updater/blob/master/factorio-mod-updater) and [Factorio Updater](https://github.com/narc0tiq/factorio-updater) so big thanks to you for your inspiration !

## Installation ##

This script has been tested (only on Debian) with Python 2.7 and 3.9 using [Requests](http://requests.readthedocs.org/en/latest/) and [Packaging](https://pypi.org/project/packaging).

1. Clone this repository in any directory. Here, `/opt/factorio-mod-manager` as an example.
```shell script
git clone git@github.com:Tantriss/Factorio-mod-manager.git /opt/factorio-mod-manager
```

2. Install the required dependency by running 

```shell script
pip install -r requirements.txt
```

If you can only use `easy_install` and not `pip`, try doing 

```shell script
easy_install `cat requirements.txt`
```

## Configuration ##

Some constant parameters can be put in a config file. These options are (option | default | definition):

* **verbose** | false | Enable verbose (debug messages) mode.

* **disable_mod_manager_update** | false | If true, disable the auto-update of this script (done via `git pull`).

* **factorio_path** | none *(not set)* | The path to the root folder of your Factorio installation.

* **username** | none *(not set)* | Your username, see [Username and token](#username-and-token).

* **token** | none *(not set)* | Your token, see [Username and token](#username-and-token).

* **should_downgrade** | false | If true, the script will install older version if no compatible version is found for the current Factorio version (see: [this note on mods not updating](#a-note-on-mod-not-installing--updating)).

* **install_required_dependencies** | true | If true, all required dependencies (and any required child dependencies) will be installed.

* **install_optional_dependencies** | false | If true, all optional dependencies will be installed. Note : optional dependencies of required/optional dependencies are never installed automatically.

* **remove_required_dependencies** | true | If true, all required dependencies (and any required child dependencies) will be removed when a parent is removed.

* **ignore_conflicts_dependencies** | false | If true, any conflict between mods are ignored and mods are installed anyway.

* **should_reload** | false | If true, the script will try to reload Factorio via systemctl and the service_name parameter

* **service_name** | none *(not set)* | If Factorio is started via a service and you want to restart it automatically



An example file can be found in this repo, just copy `config.example.json` to `config.json` and edit values inside.

Keep in mind that any corresponding command line argument will **override** these in config file.

## Usage ##

From there, it's really simple: go in the folder you where you cloned this repo earlier, and run it (try it with `--help` first!). Here's an example session:

```shell script
$ python mods_manager.py -h
usage: mods_manager.py [-h] [-p FACTORIO_PATH] [-u USERNAME] [-t TOKEN] [-d] [-i MOD_NAME_TO_INSTALL] [-U] [-e] [-l] [-r REMOVE_MOD_NAME] [-E ENABLE_MODS_NAME] [-D DISABLE_MODS_NAME] [--downgrade] [--reload] [-s SERVICE_NAME] [-v]        
                       [-nmmu] [-nrd] [-iod] [-rrd] [-rod] [-icd]                                                                                                                                                                             
                                                                                                                                                                                                                                              
Install / Update / Remove mods for Factorio

optional arguments:
  -h, --help            show this help message and exit
  -p FACTORIO_PATH, --path-to-factorio FACTORIO_PATH
                        Path to your Factorio folder.
  -u USERNAME, --user USERNAME
                        Your Factorio username, from player-data.json.
  -t TOKEN, --token TOKEN
                        Your Factorio token, from player-data.json.
  -d, --dry-run         Don't download files, just state which mods updates would be downloaded.
  -i MOD_NAME_TO_INSTALL, --install MOD_NAME_TO_INSTALL
                        Install the given mod. See README to easily find the correct mod name.
  -U, --update          Enable the update process. By default, all mods are updated. Seed -e/--update-enabled-only.
  -e, --update-enabled-only
                        Will only updates mods 'enabled' in 'mod-list.json'.
  -l, --list            List installed mods and return. Ignore other switches.
  -r REMOVE_MOD_NAME, --remove REMOVE_MOD_NAME
                        Remove specified mod.
  -E ENABLE_MODS_NAME, --enable ENABLE_MODS_NAME
                        A mod name to enable. Repeat the flag for each mod you want to enable.
  -D DISABLE_MODS_NAME, --disable DISABLE_MODS_NAME
                        A mod name to disable. Repeat the flag for each mod you want to disable.
  --downgrade           If no compatible version is found, install / update the last mod version for precedent Factorio version.
                        (ex: If mod has no Factorio 1.0.0 version, it will install the latest mod version for Factorio 0.18)
  --reload              Enable the restarting of Factorio if any mods are installed / updated. If set, service-name must be set.
  -s SERVICE_NAME, --service-name SERVICE_NAME
                        The service name used to launch Factorio. Do not pass anything if not the case (prevent reloading).
  -v, --verbose         Print URLs and stuff as they happen.
  -nmmu, --no-mod-manager-update
                        Disable the checking of Factorio-mod-manager updates. Please disable it ONLY if you encounter errors with this feature (eg: you don't have git installed).
  -nrd, --no-required-dependencies
                        Disable the auto-installation of REQUIRED dependencies.
  -iod, --install-optional-dependencies
                        Enable the auto-installation of OPTIONAL dependencies.
  -rrd, --remove-required-dependencies
                        Enable the removal of all the REQUIRED dependencies of the mod asked to be removed.
  -rod, --remove-optional-dependencies
                        Enable the removal of all the OPTIONAL dependencies of the mod asked to be removed.
  -icd, --ignore-conflicts-dependencies
                        Ignore any conflicts between mods.
```

--------

### More complex example :

Here we want to :

* Install "bobvehicleequipment"
* Enable "bobplates" and "bobgreenhouse" (assuming they are already installed)
* Disable "IndustrialRevolution" because of incompatibility issues with bob's mods
* Finally we update all mods

All this can be done in one command :
```shell script
$ python mods_manager.py -p /app/projects/factorio/factorio -u YOUR_USER -t YOUR_TOKEN -i bobvehicleequipment -E bobplates -E bobgreenhouse -D IndustrialRevolution -U
Enabling mod(s) ['bobplates', 'bobgreenhouse']

Disabling mod(s) ['IndustrialRevolution']


Installing dependency "boblibrary" version >= "1.1.0" for "bobvehicleequipment"
[==================================================]
Installed mod boblibrary version 1.1.2 for Factorio version 1.1
[==================================================]
Installed mod bobvehicleequipment version 1.1.2 for Factorio version 1.1

The mod configuration changed and Factorio need to be restarted in order to apply the changes.
Automatic reload has been disabled, please restart Factorio by yourself.
Finished !
```

## Username and token ##

The keen-eyed will have noticed the options for `--user` and `--token`. These
allow you to supply a username and token normally used by the Factorio (like the in-game updater and authenticated multiplayer). Having them will
allow you to download the mods from the [Factorio API](https://mods.factorio.com/api/mods).

First, how to get them:
* Go to [the Factorio website](https://www.factorio.com/login) and login to your account.
* Click your username in top right to go to your profile.

## How to find the correct mod name

In order to use this script, you have to find the correct mod name, not the "friendly" one.
You can do it directly from mod portal !

Once you find an interesting mod, for example `Bob's Metals, Chemicals and Intermediates`, open the mod portal page, here https://mods.factorio.com/mod/bobplates

The correct mod name to use is the last part of the URL : `bobplates`.

## A note on mod not installing / updating

When Factorio is updated to a newer version, it sometimes don't break / change anything for some mods.

This create a situation where (for example) there is no version listed of FNEI for Factorio 1.0.0
([api response](https://mods.factorio.com/api/mods/FNEI)) because the latest mod version for Factorio 0.18 works fine.

The only way to install this mod when using Factorio 1.0.0 is by using the `--downgrad` flag.
The script will now install / update the mod using the latest release available for Factorio < 1.0.0 (here Factorio 0.18).

Beware that it don't check if the mod is compatible and should only by used if you're sure that all your mods
are compatible with your Factorio version.

## About dependencies

### Dependencies when installing

By default the script will install any **required** dependencies. If a dependency has a required dependency, the script will install it as long as there is required dependencies.

This behavior can be disabled (however not recommended) by passing the `-nrd` or `--no-required-dependencies` flag.

Optional dependencies are not installed by default. It can be done by passing the `-iod` or `--install-optional-dependencies` flag.
Note that only optional dependencies of mod you are currently installing are installed. The optional dependencies of dependencies are ignored. They should be installed on their own.

### Dependencies when removing

When removing a mod, any **required** dependencies by this mods and their children will be deleted.

This behavior can be disabled by passing the `-nrrd` or `--no-remove-required-dependencies` flag.

Optional dependencies are not removed by default. It can be done by passing the `-rod` or `--remove-optional-dependencies` flag.
Note that only optional dependencies of mod you are currently removing are removed.

### Conflicts

The script will check for conflict between the mods already installed and the mod you are trying to install.

If a conflict is found, the installation stop.

To install anyway, you may use the flag `-icd` or `--ignore-conflicts-dependencies` to bypass this restriction (however really not recommended).

## License ##

The source of **Factorio Mod Manager** is Copyright 2019 Tristan "Tantrisse"
Chanove. It is licensed under the [MIT license][mit], available in this
package in the file [LICENSE.md](LICENSE.md).

[mit]: http://opensource.org/licenses/mit-license.html


## TODO ##
- Add crontab example
- Interactive mod
- Handle dependencies
- Handle conflicts
- ~~Support multiple instances of Factorio (will not do)~~
