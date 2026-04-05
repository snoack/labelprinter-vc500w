#!/usr/bin/env python3
#
# Copyright (c) Andrea Micheloni 2021
# Copyright (c) Sebastian Noack 2026
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse, json
import gzip
import os
import sqlite3
from contextlib import closing
                                      
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import argcomplete
except ImportError:
    argcomplete = None

import tempfile
import io

import mimetypes

PRINT_LOG_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS prints (
        byte_size INTEGER NOT NULL,
        width     INTEGER NOT NULL,
        height    INTEGER NOT NULL,
        error     TEXT
    )
'''

def _get_deprecated_kwargs():
    parser = argparse.ArgumentParser(add_help=False)

    try:
        parser.add_argument('--deprecated-check', action='store_true', deprecated=True)
    except TypeError:
        return {}

    return {'deprecated': True}

DEPRECATED_ARGUMENT_KWARGS = _get_deprecated_kwargs()

def get_argument_parser():
    parser = argparse.ArgumentParser(description='Remotely control a VC-500W via TCP/IP.', allow_abbrev=False, add_help=False, prog=os.environ.get('_PROG'));
    parser.add_argument('-?', '--help', action='help', help='show this help message and exit');
    parser.add_argument('-h', '--host', default='192.168.0.1', help='the VC-500W\'s hostname or IP address, defaults to %(default)s');
    parser.add_argument('-p', '--port', type=int, default=9100, help='the VC-500W\'s port number, defaults to %(default)s');

    command_group = parser.add_argument_group('command argument')

    group = command_group.add_mutually_exclusive_group(required=True);
    group.add_argument('--print-image', dest='print_image', type=argparse.FileType('rb'), action='store', metavar='IMAGE', help='prints a JPEG image, or converts another image format if Pillow is available');
    group.add_argument('--print-jpeg', dest='print_image', type=argparse.FileType('rb'), action='store', metavar='IMAGE', help='deprecated alias for --print-image', **DEPRECATED_ARGUMENT_KWARGS);
    group.add_argument('--get-status', action='store_true', help='connects to the VC-500W and returns its status');
    group.add_argument('--release', type=str, metavar='JOB_ID', help='tries to release the printer from an unclean lock earlier on');

    print_group = parser.add_argument_group('print options')

    print_group.add_argument('--print-lock', action='store_true', help='use the lock/release mechanism for printing (error prone, do not use unless strictly required)');
    print_group.add_argument('--print-mode', choices=['vivid', 'normal'], default='vivid', help='sets the print mode for a vivid or normal printing, defaults to %(default)s');
    print_group.add_argument('--print-cut', choices=['none', 'half', 'full'], default='full', help='sets the cut mode after printing, either not cutting (none), allowing the user to slide to cut (half) up to a complete cut of the label (full), defaults to %(default)s');
    print_group.add_argument('--force', action='store_true', help='skip the failed-print safeguard and send the image even if a smaller image caused the printer to lock up before');
    print_group.add_argument('--wait-after-print', action='store_true', help='wait for the printer to turn idle after printing before returning');

    status_group = parser.add_argument_group('status options')
    status_group.add_argument('-j', '--json', action='store_true', help='return the status information in JSON format');

    return parser

def _get_configuration_and_display_connection(printer):
    configuration = printer.get_configuration();

    tape_info = None;

    if configuration.tape_width:
        tape_info = '%smm tape inserted.' % int(configuration.tape_width * 25.4);
    else:
        tape_info = 'no tape detected.'
        
    print('Connected to the VC-500W [model %s]: %s' % (configuration.model, tape_info));

    return configuration

def get_status_json(printer):
    configuration = printer.get_configuration();

    device_json = {'model': configuration.model, 'serial': configuration.serial, 'wlan_mac': configuration.wlan_mac};
    

    status = printer.get_status();
    status_json = {'state': status.print_state, 'job_stage': status.print_job_stage, 'job_error': status.print_job_error};

    tape_remain = '';

    if configuration.tape_length_initial and status.tape_length_remaining != -1.0:
        mm_total = configuration.tape_length_initial * 2.54;
        mm_remain = status.tape_length_remaining * 2.54;

        tape_json = {'present': True, 'type': int(configuration.tape_width * 25.4), 'total': int(mm_total), 'remain': int(mm_remain)};
    else:
        tape_json = {'present': False};

    json_result = {'connected': True, 'device': device_json, 'tape': tape_json, 'status': status_json};

    print(json.dumps(json_result));

def get_status(printer):    
    configuration = _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    tape_remain = '';

    if configuration.tape_length_initial and status.tape_length_remaining != -1.0:
        mm_total = configuration.tape_length_initial * 2.54;
        mm_remain = status.tape_length_remaining * 2.54;
        tape_percent = mm_remain * 100 / mm_total;

        tape_remain = ' Remaining tape %s%% (%smm out of %smm).' % (int(tape_percent), int(mm_remain), int(mm_total));

    print('Status is (%s, %s, %s).%s' % (status.print_state, status.print_job_stage, status.print_job_error, tape_remain));

def _connect_database():
    state_home = os.environ.get('XDG_STATE_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'state')
    log_directory = os.path.join(state_home, 'labelprinter-vc500w')
    os.makedirs(log_directory, exist_ok = True)
    return sqlite3.connect(os.path.join(log_directory, 'data.db'))

def _prepare_image_for_print(image_file):
    file_type = mimetypes.guess_type(image_file.name)[0]
    needs_conversion = file_type != 'image/jpeg'

    if Image is None:
        if needs_conversion:
            print('PRINT FAILED: not a JPEG file')
            raise SystemExit(1)

        return image_file, None

    if needs_conversion:
        print('Input is %s, converting to jpeg' % (file_type if file_type is not None else 'an unknown format'))

    try:
        with Image.open(image_file) as image:
            image_size = image.size
            if needs_conversion:
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg')
                image.convert('RGB').save(temp_file, format='JPEG')
                image_file.close()
                image_file = temp_file
    except Exception as error:
        print('PRINT FAILED: image processing error: %s' % error)
        raise SystemExit(1)

    image_file.seek(0)
    return image_file, image_size

def _append_print_log(db, image_file, image_size, error = None):
    if image_size is None:
        return

    with db:
        db.execute(
            'INSERT INTO prints (byte_size, width, height, error) VALUES (?, ?, ?, ?)',
            (
                os.path.getsize(image_file.name),
                image_size[0],
                image_size[1],
                error,
            )
        )

def _has_matching_failed_print(db, image_file, image_size):
    if image_size is None:
        return False

    short_side, long_side = sorted(image_size)
    return bool(db.execute(
        'SELECT 1 FROM prints '
        'WHERE error IS NOT NULL '
        'AND min(width, height) <= ? '
        'AND max(width, height) <= ? '
        'AND byte_size <= ? '
        'LIMIT 1',
        (
            short_side,
            long_side,
            os.path.getsize(image_file.name),
        )
    ).fetchone())

def print_image(printer, use_lock, mode, cut, image_file, wait_after_print, force):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    if use_lock:
        lock = printer.lock(); 
        print('Printer locked with message "%s", started printing job %s...' % (lock.comment, lock.job_number));

    try:
        if use_lock:
            job_status = printer.get_job_status();
            print('Job status: %s, %s, %s. Sending the print command...' %(job_status.print_state, job_status.print_job_stage, job_status.print_job_error));

        image_file, image_size = _prepare_image_for_print(image_file)
        with image_file, closing(_connect_database()) as db:
            db.execute(PRINT_LOG_SCHEMA)

            if not force and _has_matching_failed_print(db, image_file, image_size):
                print('PRINT FAILED: matched a no-larger failed print. Use --force to bypass.')
                raise SystemExit(1)

            try:
                printer.print_jpeg(image_file, mode, cut)
                if wait_after_print:
                    printer.wait_to_turn_idle()
            except Exception as error:
                print('PRINT FAILED: printer error: %s' % error)
                # Only log bad printer responses here. We use these records to
                # block future prints of the same or larger size, so transient
                # errors such as an unreachable printer should not be recorded.
                if isinstance(error, ValueError):
                    _append_print_log(db, image_file, image_size, str(error))
                raise SystemExit(1)
            print("PRINT OK")
            _append_print_log(db, image_file, image_size)
    finally:
        if use_lock:
            print('Releasing lock for job %s...' % lock.job_number);
            printer.release();

def release_lock(printer, job_id):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    print('Releasing lock for job %s...' % job_id);
    printer.release(job_id);

def main():
    from labelprinter.connection import Connection
    from labelprinter.printer import LabelPrinter

    parser = get_argument_parser()
    if argcomplete is not None:
        argcomplete.autocomplete(parser, exclude=['--print-jpeg'])

    args = parser.parse_args()
    connection = None;
    try:
        printer = LabelPrinter(Connection(args.host, args.port))

        if args.get_status:
            if args.json:
                get_status_json(printer);
            else:
                get_status(printer);
        elif args.print_image != None:
            print_image(printer, args.print_lock, args.print_mode, args.print_cut, args.print_image, args.wait_after_print, args.force)
        elif args.release != None:
            release_lock(printer, args.release);
        else:
            raise ValueError('Unreachable code.');
    except:
        if args.get_status and args.json:
            print(json.dumps({'connected': False}));
            return;
        raise;
    finally:
        if connection:
            connection.close();

if __name__ == "__main__":
    main();
