# Brother VC-500W Label Printer CLI

This repository contains a command-line tool for controlling a [Brother VC-500W](https://www.brother.com.hk/en/labellers/vc500w.html) label printer over TCP/IP.

This project is a fork of https://gitlab.com/lenchan139/labelprinter-vc500w, which itself was forked from https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/.

Licensed under AGPL-3.0-or-later. See [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial, community-maintained tool. It is not affiliated with or supported by Brother. You are responsible for how you use it, and it may behave unexpectedly or interact poorly with your printer.

## Installation

### On Debian/Ubuntu

You can install `labelprinter-vc500w` via [`deb-get`](https://github.com/wimpysworld/deb-get):

```sh
sudo deb-get install labelprinter-vc500w
```

Alternatively, download the latest `.deb` package from the [Releases](https://github.com/snoack/labelprinter-vc500w/releases) page for this repository and install it with `apt`:

```sh
sudo apt install ./labelprinter-vc500w_<version>_all.deb
```

### From PyPI

```sh
pipx install labelprinter-vc500w
```

## Finding your printer

You must pass the printer's IP address with `--host`.

If you do not know the printer IP, you can find it with the official Brother app or by scanning your local network. On Debian and Ubuntu, one option is `nbtscan`:

```sh
sudo apt install nbtscan
nbtscan -v -s : 192.168.1.1/24 | grep "VC-500W"
```

## Usage

You can either install this script (see above) or run it from a checkout of this repository.

Minimum request to print an image:

```sh
# if installed
bclprinter --host 192.168.5.5 --print-image /home/user/my_screenshot.jpeg

# from a checkout
./labelprinter.sh --host 192.168.5.5 --print-image /home/user/my_screenshot.jpeg
```

Print with additional options:

```sh
# if installed
bclprinter --host 192.168.5.5 --print-mode vivid --print-cut full --print-image /home/user/my_screenshot.jpeg

# from a checkout
./labelprinter.sh --host 192.168.5.5 --print-mode vivid --print-cut full --print-image /home/user/my_screenshot.jpeg
```

If a print job is done or jammed but the printer still appears locked, release the stale job lock with:

```sh
# if installed
bclprinter --host 192.168.5.5 --release JOB_ID

# from a checkout
./labelprinter.sh --host 192.168.5.5 --release JOB_ID
```

## Command reference

The module can be started with the included `labelprinter.sh` helper script or via `python3 -m labelprinter`. The current command-line interface is:

```
usage: labelprinter.sh [-?] [-h HOST] [-p PORT]
                       (--print-image IMAGE | --print-jpeg IMAGE | --get-status | --release JOB_ID)
                       [--print-lock] [--print-mode {vivid,normal}]
                       [--print-cut {none,half,full}] [--wait-after-print]
                       [-j]

Remotely control a VC-500W via TCP/IP.

optional arguments:
  -?, --help            show this help message and exit
  -h HOST, --host HOST  the VC-500W's hostname or IP address, defaults to
                        192.168.0.1
  -p PORT, --port PORT  the VC-500W's port number, defaults to 9100

command argument:
  --print-image IMAGE   prints a JPEG image, or converts another image format
                        if Pillow is available
  --print-jpeg IMAGE    deprecated alias for --print-image
  --get-status          connects to the VC-500W and returns its status
  --release JOB_ID      tries to release the printer from an unclean lock
                        earlier on

print options:
  --print-lock          use the lock/release mechanism for printing (error
                        prone, do not use unless strictly required)
  --print-mode {vivid,normal}
                        sets the print mode for a vivid or normal printing,
                        defaults to vivid
  --print-cut {none,half,full}
                        sets the cut mode after printing, either not cutting
                        (none), allowing the user to slide to cut (half),
                        or performing a complete cut (full), defaults to full
  --wait-after-print    wait for the printer to turn idle after printing
                        before returning

status options:
  -j, --json            return the status information in JSON format
```

## Technical details

Read the original post, thank you.
https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/
