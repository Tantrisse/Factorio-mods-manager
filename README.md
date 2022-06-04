This is a tool for [Factorio](http://www.factorio.com/) headless server management.
It provides mod management : List / Install / Update / Remove / Enable / Disable.

This package is heavily inspired by [Factorio-mod-updater](https://github.com/astevens/factorio-mod-updater/blob/master/factorio-mod-updater) and [Factorio Updater](https://github.com/narc0tiq/factorio-updater) so big thanks to you for your inspiration !

## Coming from [Factorio-Init](https://github.com/Bisa/factorio-init) ? 

If you found this script by using [Factorio-Init](https://github.com/Bisa/factorio-init) and want a quick setup, just follow the installation step and... that's all ! [Factorio-Init](https://github.com/Bisa/factorio-init) will pass any needed configuration to [Factorio-mods-manager](https://github.com/Tantrisse/Factorio-mods-manager) (Path to factorio, Username, Token) !

You can still copy and edit the `config.json` file (see [Configuration](#configuration)) to customise the way the script works.

Keep in mind that if you invoke this script via [Factorio-Init](https://github.com/Bisa/factorio-init) (`./factorio mod install XXXX`) these options are ignored from the `config.json` file as they come from [Factorio-Init](https://github.com/Bisa/factorio-init) :
- factorio_path
- username
- token
- alternative_glibc_directory
- alternative_glibc_version

## Installation ##

This script has been tested (only on Debian) with Python 2.7 and 3.9 using [Requests](http://requests.readthedocs.org/en/latest/) and [Packaging](https://pypi.org/project/packaging).

1. Clone this repository in any directory. Here, `/opt/factorio-mod-manager` as an example.
```shell script
git clone git@github.com:Tantrisse/Factorio-mods-manager.git /opt/factorio-mod-manager
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

Some constant parameters can be put in a config file. The mandatory options which don't have a default values are `factorio_path`, `username` and `token`, these must be set via command line parameters or the config file.

All other options have default value 

These options are 

|                            Option | Default | Definition                                                                                                                                                                                          |
|----------------------------------:|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|                 **factorio_path** | none    | The path to the root folder of your Factorio installation.                                                                                                                                          |
|                      **username** | none    | Your username, see [Username and token](#username-and-token).                                                                                                                                       |
|                         **token** | none    | Your token, see [Username and token](#username-and-token).                                                                                                                                          |
|                       **verbose** | false   | Enable verbose (debug messages) mode.                                                                                                                                                               |
|              **should_downgrade** | false   | If true, the script will install older version if no compatible version is found for the current Factorio version (see: [this note on mods not updating](#a-note-on-mod-not-installing--updating)). |
| **install_required_dependencies** | true    | If true, all required dependencies (and any required child dependencies) will be installed.                                                                                                         |
| **install_optional_dependencies** | false   | If true, all optional dependencies will be installed. Note : optional dependencies of required/optional dependencies are never installed automatically.                                             |
|  **remove_required_dependencies** | true    | If true, all required dependencies (and any required child dependencies) will be removed when a parent is removed.                                                                                  |
|  **remove_optional_dependencies** | false   | If true, all optional dependencies will be removed when a parent is removed. Note : optional dependencies of required/optional dependencies are never removed automatically.                        |
| **ignore_conflicts_dependencies** | false   | If true, any conflict between mods are ignored and mods are installed anyway.                                                                                                                       |
|                 **should_reload** | false   | If true, the script will try to reload Factorio via systemctl and the service_name parameter.                                                                                                       |
|                  **service_name** | none    | If Factorio is started via a service and you want to restart it automatically.                                                                                                                      |
|   **alternative_glibc_directory** | false   | Absolute path to the side by side GLIBC root, used for systems using older glibc versions (RHEL CentOS and others...)                                                                               |
|     **alternative_glibc_version** | false   | Version of alt GLIBC (2.18 is the minimum required for factorio)                                                                                                                                    |

An example file can be found in this repo, just copy `config.example.json` to `config.json` and edit values inside.

Keep in mind that any corresponding command line argument will **override** these in config file.

## Usage ##

There is too many possibilities to cover them all here ! You can get a summary of all commands and flags by simply going in the folder where you cloned this repo, and run 

```shell script
python mods_manager.py --help
```

--------

### A complex example :

Here we want to :

* Install "bobvehicleequipment"
* Enable "bobplates" and "bobgreenhouse" (assuming they are already installed)
* Disable "IndustrialRevolution" because of incompatibility issues with Bob's mods
* Finally, we update all mods

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

## On the error "version `GLIBC_2.18' not found"

If you encounter an error about **GLIBC 2.18** not found, you can install it using [this thread on the factorio forum by **millisa**](https://forums.factorio.com/viewtopic.php?t=54654#p324493).

When following the aforementioned guide, if you stumble across the error `These critical programs are missing or too old: make` when doing `../configure --prefix='/opt/glibc-2.18'` and your make version is up-to-date, just run this command and try again :
```
sed "s/3\.\[89\]/3\.\[89\]\* | 4/" -i ../configure
```
You should be able to finish the installation of GLIBC.

After that, you need to add to the `config.json` file of `Factorio-mod-manager` these 2 key : `alternative_glibc_directory` and `alternative_glibc_version`.

You can use the command line parameters `--alternative-glibc-directory` and `--alternative-glibc-version` instead of the `config.json` file.

See [the part about configuration](#configuration) to know what value to pass.

## A note on mod not installing / updating

When Factorio is updated to a newer version, it sometimes doesn't break / change anything for some mods.

This creates a situation where (for example) there is no version listed of FNEI for Factorio 1.0.0
([api response](https://mods.factorio.com/api/mods/FNEI)) because the latest mod version for Factorio 0.18 works fine.

The only way to install this mod when using Factorio 1.0.0 is by using the `--downgrad` flag.
The script will now install / update the mod using the latest release available for Factorio < 1.0.0 (here Factorio 0.18).

Beware that it don't check if the mod is compatible and should only be used if you're sure that all your mods
are compatible with your Factorio version.

## About dependencies

### Dependencies when installing

By default, the script will install any **required** dependencies. If a dependency has a required dependency, the script will install it as long as there is required dependencies.

This behavior can be disabled (however not recommended) by passing the `-nrd` or `--no-required-dependencies` flag.

Optional dependencies are not installed by default. It can be done by passing the `-iod` or `--install-optional-dependencies` flag.
Note that only optional dependencies of mod you are currently installing are installed. The optional dependencies of dependencies are ignored. They should be installed on their own.

### Dependencies when removing

When removing a mod, any **required** dependencies by this mod and their children will be deleted.

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
- ~~Handle dependencies~~ (done, should update do it too ? Probably)
- ~~Handle conflicts~~ (kinda done)
- ~~Support multiple instances of Factorio~~ (will not do)
