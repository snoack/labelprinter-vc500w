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

The module can be started with the included `labelprinter.sh` helper script or via `python3 -m labelprinter`.

For the full CLI reference, please refer to the built-in help or the man page:

```sh
# if installed
bclprinter --help
man bclprinter

# from a checkout
./labelprinter.sh --help
```

## Technical details

Read the original post, thank you.
https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/
