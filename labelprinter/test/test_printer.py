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

import unittest, logging
from pathlib import Path

from labelprinter.printer import *

logger = logging.getLogger(__name__)
TEST_DIR = Path(__file__).resolve().parent


class MockConnection(object):
    def __init__(self):
        self._sent = []
        self._responses = {}
        self._last_message = None

    def dump_responses(self):
        logger.debug("Configured responses: %s", self._responses)

    def register_response(self, message, response, answer_description):
        self._responses[message] = (answer_description, response)

    def register_response_from_files(self, file_message, file_response, answer_description):
        logger.debug("Registering message/response pair in mock from files %s and %s", file_message, file_response)

        return self.register_response((TEST_DIR / file_message).read_text().rstrip(), (TEST_DIR / file_response).read_text().rstrip(), answer_description)

    def register_binary_response(self, file_message, file_response, answer_description):
        logger.debug("Registering message/response pair in mock from files (binary)%s and (ASCII)%s", file_message, file_response)

        return self.register_response((TEST_DIR / file_message).read_bytes(), (TEST_DIR / file_response).read_text().rstrip(), answer_description)

    def send_message(self, message):
        data = message.get_data()

        logger.info("Received message of type %s: %s", type(message).__name__, data.encode())

        self._last_message = data

    def send_file(self, handle):
        binary_data = Path(handle.name).read_bytes()

        logger.info("Received binary file to send, totalling %s bytes", len(binary_data))

        self._last_message = binary_data

    def get_message(self, long_timeout = False, buffer_size = 4096):
        logger.info("Mock has been asked for a response to the last message")

        if self._last_message in self._responses:
            answer_description, data = self._responses[self._last_message]

            logger.info("Returning %s: %s", answer_description, data.encode())

            return data
        else:
            error="No response has been configured in the mock for message %s" % self._last_message.encode()

            logger.error(error)
            self.dump_responses()

            raise ValueError(error)

class TestPrinter(unittest.TestCase):
    def test_00_init(self):
        """Tests instantiating a LabelPrinter object"""

        printer = LabelPrinter(MockConnection())

        logger.info("Got printer: %s", printer)

        self.assertIsNotNone(printer)

    def _assert_get_configuration(self, message, response, answer_description, tape_type, tape_length_initial, tape_width, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(message, response, answer_description)

        result = printer.get_configuration()

        logger.info("Got result: %s", result)
        
        self.assertEqual(Config, type(result));
        self.assertEqual("Wedge", result.model);
        self.assertEqual("XXXXXXXXXXXXXXX", result.serial);
        self.assertEqual("00:00:00:00:00:00", result.wlan_mac);
        self.assertEqual(tape_type, result.tape_type);
        self.assertEqual(tape_length_initial, result.tape_length_initial);
        self.assertEqual(tape_width, result.tape_width);

        return result

    def test_get_configuration(self):
        """Tests getting the configuration off a printer"""

        result = self._assert_get_configuration('getconfig.bin', 'getconfig.resp.bin', 'configuration XML', 1, 197.0, 1.022)
        
    def test_get_configuration_no_tape(self):
        """Tests getting the configuration off a printer (no tape inserted)"""

        result = self._assert_get_configuration('getconfig.bin', 'getconfig2.resp.bin', 'configuration XML (no tape)', '', '', '')

    def _assert_get_status(self, message, response, answer_description, print_state, print_job_stage, print_job_error, tape_length_remaining, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(message, response, answer_description)

        result = printer.get_status()

        logger.info("Got result: %s", result)
        
        self.assertEqual(Status, type(result));
        self.assertEqual(print_state, result.print_state)
        self.assertEqual(print_job_stage, result.print_job_stage)
        self.assertEqual(print_job_error, result.print_job_error)
        self.assertEqual(tape_length_remaining, result.tape_length_remaining)

    def test_get_status_idle_after_boot(self):
        """Tests getting the status off an idle printer (after boot)"""

        result = self._assert_get_status('getstatus.bin', 'getstatus3.resp.bin', 'status XML (idle)', 'IDLE', 'READY FOR PRINT', 'NONE', 180.96)

    def test_get_status_idle_after_job(self):
        """Tests getting the status off an idle printer (after printing)"""

        result = self._assert_get_status('getstatus.bin', 'getstatus.resp.bin', 'status XML (idle)', 'IDLE', 'SUCCESS', 'NONE', 179.31)

    def test_get_status_printing(self):
        """Tests getting the status off a printer whilst printing"""

        result = self._assert_get_status('getstatus.bin', 'getstatus2.resp.bin', 'status XML (printing)', 'BUSY', 'PRINTING', 'NONE', 179.31)

    def _assert_lock_status(self, message, response, answer_description, operation, job_number, code, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(message, response, answer_description)

        result = printer.lock()

        logger.info("Got result: %s", result)
        
        self.assertEqual(LockAnswer, type(result));
        self.assertEqual(job_number, result.job_number)
        self.assertEqual(code, result.code)

    def test_lock(self):
        """Tests locking the printer before printing"""

        result = self._assert_lock_status('lock.bin', 'lock.resp.bin', 'lock request XML', 'set', 'L1807901834', 0)

    def _assert_release_status(self, message, response, answer_description, operation, job_number, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(message, response, answer_description)

        result = printer.release(job_number)

        logger.info("Got result: %s", result)
        
        self.assertEqual(ReleaseAnswer, type(result));

    def test_lock_release(self):
        """Tests releasing the printer lock after printing"""

        result = self._assert_release_status('release.bin', 'release.resp.bin', 'release request XML', 'cancel', 'L1807901834')

    def _assert_print(self, setup_message, setup_response, setup_description, image, image_response, image_description, mode, cut, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(setup_message, setup_response, setup_description)
        printer._connection.register_binary_response(image, image_response, image_description)

        with (TEST_DIR / image).open('rb') as image_handle:
            result = printer.print_jpeg(image_handle, mode, cut)

        logger.info("Got result: %s", result)
        
        self.assertEqual(PrintAnswer, type(result));

    def test_print_image(self):
        """Tests printing a test image"""

        result = self._assert_print('printsetup.bin', 'printsetup.resp.bin', 'print setup XML', 'image.jpg', 'image.resp.bin', 'image binary data', 'vivid', 'full')

    def _assert_print_with_lock(self, lock_message, lock_response, lock_description, release_message, release_response, release_description, job_number, code, setup_message, setup_response, setup_description, image, image_response, image_description, mode, cut, printer = LabelPrinter(MockConnection())):
        printer._connection.register_response_from_files(lock_message, lock_response, lock_description)

        self._assert_lock_status(lock_message, lock_response, lock_description, 'set', job_number, code, printer)
        self._assert_print(setup_message, setup_response, setup_description, image, image_response, image_description, mode, cut, printer = printer)
        self._assert_release_status(release_message, release_response, release_description, 'cancel', job_number, printer = printer)

    def test_print_image_with_lock(self):
        """Tests printing a test image with a lock"""

        result = self._assert_print_with_lock('lock.bin', 'lock.resp.bin', 'lock request XML', 'release.bin', 'release.resp.bin', 'release request XML', 'L1807901834', 0, 'printsetup2.bin', 'printsetup.resp.bin', 'print setup XML', 'image.jpg', 'image.resp.bin', 'image binary data', 'normal', 'half')
