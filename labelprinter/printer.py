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


import re, os, time;

class LabelPrinter:
    def __init__(self, connection):
        self._active_job = None;
        self._connection = connection;
        self._errors = 0;

    def _send_and_expect(self, question, answer_class):
        self._connection.send_message(question);
        data = self._connection.get_message();

        return answer_class(data, self._connection.get_message);

    def get_configuration(self):
        return self._send_and_expect(GetConfig(), Config);

    def get_status(self):
        return self._send_and_expect(GetStatus(), Status);

    def get_job_status(self):
        return self._send_and_expect(GetStatus(self._active_job), Status);

    def lock(self):
        lock = self._send_and_expect(Lock(), LockAnswer);   

        self._active_job = lock.job_number;

        return lock;

    def release(self, job_number = None):
        if job_number == None:
            job_number = self._active_job;

        release = self._send_and_expect(Release(job_number), ReleaseAnswer);

        return release;

    def print_jpeg(self, handle, mode, cut):
        image_size = os.path.getsize(handle.name);

        self._send_and_expect(Print(self._active_job, image_size, mode, cut), PrintAnswer);
        self._connection.send_file(handle);

        return PrintAnswer(self._connection.get_message(), self._connection.get_message);

    def wait_to_turn_idle(self):
        job_status = None;

        while job_status == None or job_status.print_state != "IDLE":
            time.sleep(2.5);

            job_status = self.get_job_status();

class Question:
    def __init__(self, data):
        self._data = data;

    def get_data(self):
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + self._data;

class RegexReader:
    def get_numeric_XML_value_regex(self, name):
        return re.compile(r'.*<%s>(\d+)</%s>.*' % (name, name), re.I | re.S);

    def get_float_XML_value_regex(self, name):
        return re.compile(r'.*<%s>([0-9.]+)</%s>.*' % (name, name), re.I | re.S);

    def get_string_XML_value_regex(self, name):
        return re.compile(r'.*<%s>(.+)</%s>.*' % (name, name), re.I | re.S);

    def get_numeric_XML_value(self, name, data, default = None):
        match = self.get_numeric_XML_value_regex(name).match(data);

        if match:
            return int(match.group(1));
        elif default == None:
            raise ValueError('Could not parse XML for %s' % name);
        else:
            return default;

    def get_float_XML_value(self, name, data, default = None):
        match = self.get_float_XML_value_regex(name).match(data);

        if match:
            return float(match.group(1));
        elif default == None:
            raise ValueError('Could not parse XML for %s' % name);
        else:
            return default;

    def get_string_XML_value(self, name, data, default = None):
        match = self.get_string_XML_value_regex(name).match(data);

        if match:
            return match.group(1);
        elif default == None:
            raise ValueError('Could not parse XML for %s' % name);
        else:
            return default;

class AnswerStatus(RegexReader):
    def __init__(self, data):
        RegexReader.__init__(self);

        self.code = self.get_numeric_XML_value('code', data, -1);
        self.datasize = self.get_numeric_XML_value('datasize', data, -1);
        self.comment = self.get_string_XML_value('comment', data, '');

class Answer(RegexReader):
    def __init__(self, data, callback_more_data_needed):
        if data[0:47] != '<?xml version="1.0" encoding="UTF-8"?>\n<status>':
            raise ValueError('Expected a XML status response first: ' + repr(data[0:47]));
        else:
            self.comment='';
            status_end = data.find('</status>', 47);

            if status_end == -1:
                raise ValueError('Could not finish reading the XML status message.');
            else:
                expected_start = self._get_expected_start();
                status = AnswerStatus(data[0 : status_end + 9]);
                self.comment = status.comment;

                if status.code != 0:
                    if status.comment and len(status.comment)>0:
                        raise ValueError('The XML status code is not OK: "%s"' % status.comment);
                    else:
                        raise ValueError('The XML status code is not OK.');
                elif expected_start == None:
                    self._process_data(data[0:status_end+9]);
                elif status.datasize < 0:
                    raise ValueError('The XML datasize is invalid.');
                else:
                    while len(data) < status_end + status.datasize + 10:
                        missing = status_end + status.datasize - len(data) + 11;

                        data = data + callback_more_data_needed(long_timeout = False, buffer_size = missing);
                    payload_data = data[status_end + 11 : status_end + status.datasize + 10];

                    if payload_data[0:len(expected_start)].startswith(expected_start):
                        self._process_data(payload_data);
                    else:
                        raise ValueError('Expected the payload starting with the specific XML message.');


    def _processData(self, data):
        pass

class GetConfig(Question):
    def __init__(self):
        Question.__init__(self, '<read>\n<path>/config.xml</path>\n</read>');

class Config(Answer):
    def _get_expected_start(self):
        return '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n';

    def _process_data(self, data):
        self.model = self.get_string_XML_value('model_name', data);
        self.serial = self.get_string_XML_value('serial_number', data);
        self.wlan_mac = self.get_string_XML_value('wlan0_mac_address', data);
        self.tape_type = self.get_numeric_XML_value('cassette_type', data, '');
        self.tape_length_initial = self.get_float_XML_value('media_length_initial', data, '');
        self.tape_width = self.get_float_XML_value('width_inches', data, '');

class GetStatus(Question):
    def __init__(self, job_token = None):
        if job_token == None:
            Question.__init__(self, '<read>\n<path>/status.xml</path>\n</read>');
        else:
            Question.__init__(self, '<read>\n<path>/status.xml</path>\n<job_token>%s</job_token>\n</read>' % job_token);

class Status(Answer):
    def _get_expected_start(self):
        return '<?xml version="1.0" encoding="UTF-8"?>\n<status>\n';

    def _process_data(self, data):
        self.print_state = self.get_string_XML_value('print_state', data);
        self.print_job_stage = self.get_string_XML_value('print_job_stage', data);
        self.print_job_error = self.get_string_XML_value('print_job_error', data);
        self.tape_length_remaining = self.get_float_XML_value('remain', data, -1);

class Lock(Question):
    def __init__(self):
        Question.__init__(self, '<lock>\n<op>set</op>\n<page_count>-1</page_count>\n<job_timeout>99</job_timeout>\n</lock>');

class LockAnswer(Answer):
    def _get_expected_start(self):
        return None;

    def _process_data(self, data):
        self.job_number = self.get_string_XML_value('job_token', data);
        self.code = self.get_numeric_XML_value('code', data);

class Release(Question):
    def __init__(self, job_number):
        Question.__init__(self, '<lock>\n<op>cancel</op>\n<job_token>%s</job_token>\n</lock>' % job_number);

class ReleaseAnswer(Answer):
    def _get_expected_start(self):
        return None;

    def _process_data(self, data):
        pass;

class Print(Question):
    def __init__(self, job_number, image_size, mode, cut):
        job_specification = '';

        if job_number:
            job_specification = '<job_token>%s</job_token>\n' % job_number;

        Question.__init__(self, '<print>\n<mode>%s</mode>\n<speed>%s</speed>\n<lpi>%s</lpi>\n<width>0</width>\n<height>0</height>\n<dataformat>jpeg</dataformat>\n<autofit>1</autofit>\n<datasize>%s</datasize>\n<cutmode>%s</cutmode>\n%s</print>' % (self.get_mode(mode)['name'], self.get_mode(mode)['speed'], self.get_mode(mode)['lpi'], image_size, cut, job_specification));

    def get_mode(self, mode):
        modes = {'vivid': {'name': 'vivid', 'speed': 0, 'lpi': 317}, 'normal': {'name': 'color', 'speed': 1, 'lpi': 264}}

        return modes[mode];

class PrintAnswer(Answer):
    def _get_expected_start(self):
        return None;

    def _process_data(self, data):
        pass;
