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
                                      
try:
    from PIL import Image
except ImportError:
    Image = None

import tempfile
import io

import mimetypes 
from labelprinter.connection import Connection
from labelprinter.printer import LabelPrinter

def main():
    parser = argparse.ArgumentParser(description='Remotely control a VC-500W via TCP/IP.', allow_abbrev=False, add_help=False, prog=os.environ.get('_PROG'));
    parser.add_argument('-?', '--help', action='help', help='show this help message and exit');
    parser.add_argument('-h', '--host', default='192.168.0.1', help='the VC-500W\'s hostname or IP address, defaults to %(default)s');
    parser.add_argument('-p', '--port', type=int, default=9100, help='the VC-500W\'s port number, defaults to %(default)s');

    command_group = parser.add_argument_group('command argument')

    group = command_group.add_mutually_exclusive_group(required=True);
    group.add_argument('--print-jpeg', type=argparse.FileType('rb'), action='store', metavar='JPEG', help='prints a JPEG image out of the VC-500W');
    group.add_argument('--get-status', action='store_true', help='connects to the VC-500W and returns its status');
    group.add_argument('--release', type=str, metavar='JOB_ID', help='tries to release the printer from an unclean lock earlier on');

    print_group = parser.add_argument_group('print options')

    print_group.add_argument('--print-lock', action='store_true', help='use the lock/release mechanism for printing (error prone, do not use unless strictly required)');
    print_group.add_argument('--print-mode', choices=['vivid', 'normal'], default='vivid', help='sets the print mode for a vivid or normal printing, defaults to %(default)s');
    print_group.add_argument('--print-cut', choices=['none', 'half', 'full'], default='full', help='sets the cut mode after printing, either not cutting (none), allowing the user to slide to cut (half) up to a complete cut of the label (full), defaults to %(default)s');
    print_group.add_argument('--wait-after-print', action='store_true', help='wait for the printer to turn idle after printing before returning');

    status_group = parser.add_argument_group('status options')
    status_group.add_argument('-j', '--json', action='store_true', help='return the status information in JSON format');

    process_arguments(parser.parse_args());

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

def print_jpeg(printer, use_lock, mode, cut, jpeg_file, wait_after_print):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    if use_lock:
        lock = printer.lock(); 
        print('Printer locked with message "%s", started printing job %s...' % (lock.comment, lock.job_number));

    try:
        if use_lock:
            job_status = printer.get_job_status();
            print('Job status: %s, %s, %s. Sending the print command...' %(job_status.print_state, job_status.print_job_stage, job_status.print_job_error));
        file_type = mimetypes.guess_type(jpeg_file.name)[0];
        print('Input file type is %s' % (file_type));
        if Image != None and file_type.startswith('image/') and not file_type == 'image/jpeg':
            print('Is %s but not jpeg, try convert' % file_type)
            try:
                with tempfile.NamedTemporaryFile() as tmp:
                    im1 = Image.open(jpeg_file.name)
                    imX = im1.convert('RGB')
                    pathName = tmp.name + '.jpg'
                    imX.save(pathName)
                    
                    jpeg_file = open(pathName, 'rb') 
                    old_file_type = file_type
                    file_type = mimetypes.guess_type(jpeg_file.name)[0];
                    print('%s convert to %s' % ( old_file_type, file_type))
            except:
                print('fail for convert to jpg, ')

        if file_type == 'image/jpeg':
            print_answer = printer.print_jpeg(jpeg_file, mode, cut);
            if wait_after_print:
                printer.wait_to_turn_idle();
            print("PRINT OK");
        else:
            print('not a JPEG file');
            print('PRINT FAILED');
    finally:
        if use_lock:
            print('Releasing lock for job %s...' % lock.job_number);
            printer.release();

def release_lock(printer, job_id):
    _get_configuration_and_display_connection(printer);
    status = printer.get_status();

    print('Releasing lock for job %s...' % job_id);
    printer.release(job_id);

def process_arguments(args):
    connection = None;
    try:
        printer = LabelPrinter(Connection(args.host, args.port))

        if args.get_status:
            if args.json:
                get_status_json(printer);
            else:
                get_status(printer);
        elif args.print_jpeg != None:
            print_jpeg(printer, args.print_lock, args.print_mode, args.print_cut, args.print_jpeg, args.wait_after_print);
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
