This is a tool for [Factorio](http://www.factorio.com/) headless server management.
It provides mod installation and update.

This package is heavily inspired by [Factorio-mod-updater](https://github.com/astevens/factorio-mod-updater/blob/master/factorio-mod-updater) and [Factorio Updater](https://github.com/narc0tiq/factorio-updater).

## Installation ##

Just clone this repository in any directory. Here, `/opt/factorio-mod-manager` as an example.
```shell script
git clone git@github.com:Tantriss/Factorio-mod-manager.git /opt/factorio-mod-manager 
```

I recommand you to use the same user your Factorio server has been started with, as the mods downloaded by this script will belong to this user.

This script has been tested (only on Debian) with Python 2.7 and 3.5 using a single non-standard library, [Requests](http://requests.readthedocs.org/en/latest/).

To install the required dependency, you should need do no more than run `pip
install requests` (or, `easy_install requests`). If this
does not work, you are encouraged to read the linked documentation and try to
figure out what's gone wrong.

## Usage ##

From there, it's really simple: go in the folder you where you cloned this repo earlier, and run it (try it with `--help` first!). Here's an example session:

```
$ python mods_manager.py --help
usage: mods_manager.py [-h] -p MOD_LIST_PATH -u USERNAME -t TOKEN [-d]
                       [-i MOD_NAME_TO_INSTALL] [-U] [-e] [-v]

Install and update mods (from mod_list.json) for Factorio

optional arguments:
  -h, --help            show this help message and exit
  -p MOD_LIST_PATH, --mod-list-path MOD_LIST_PATH
                        Path to your mod_list.json file. See README to find it
                        easily.
  -u USERNAME, --user USERNAME
                        Your Factorio service username, from player-data.json.
  -t TOKEN, --token TOKEN
                        Your Factorio service token, from player-data.json.
  -d, --dry-run         Don't download files, just state which mods updates
                        would be downloaded.
  -i MOD_NAME_TO_INSTALL, --install MOD_NAME_TO_INSTALL
                        Install the given mod. See README to find how easily
                        get the correct name for the mod.
  -U, --update          Enable the update process. By default, all mods are
                        updated. Seed -e/--update-enabled-only.
  -e, --update-enabled-only
                        Will only updates mods 'enabled' in 'mod_list.json'.
  -v, --verbose         Print URLs and stuff as they happen.
```
```shell script
$ python mods_manager.py -p /opt/factorio/mods/mod-list.json -u ***REMOVED*** -t ***REMOVED*** -i bobpower -U -e -v
Installing mod bobpower
Getting mod infos...
Downloading mod bobpower
[==================================================]
Parsing "mod_list.json"...
Getting mod infos...
Mod boblogistics is disable and --update-enabled-only has been used. Skipping...
Starting mods update...
Downloading mod IndustrialRevolution
[==================================================]
Downloading mod rso-mod
[==================================================]
Finished !
```

## Service username and token ##

The keen-eyed will have noticed the options for `--user` and `--token`. These
allow you to supply a username and token normally used by the Factorio services
(like the in-game updater and authenticated multiplayer). Having them will
allow you to download the mods from the [Factorio API](https://mods.factorio.com/api/mods).

First, how to get them:
* Go to [the factorio website](https://www.factorio.com/login) and login to your account.
* Click your username in top right to go to your profile.

## License ##

The source of **Factorio Mod Manager** is Copyright 2019 Tristan "Tantriss"
Chanove. It is licensed under the [MIT license][mit], available in this
package in the file [LICENSE.md](LICENSE.md).

[mit]: http://opensource.org/licenses/mit-license.html


## TODO ##

- Maybe switch install code just write mod to `mod-list.json` and run update ?
  - Seems to be a good idea as `mod-list.json` is only refreshed after the second restart of the server...
- Add mod listing
- Add mod removing
- Add crontab example
