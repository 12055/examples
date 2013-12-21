#! /usr/bin/env python

"""
                                                                                                            :::.
                                                                                                     ::::
   1G00000000G.    t00000000000f        .         :G000000000C     000000000000C   00000        ::::
  L00              C00        000      000       i00.                                10000f ::::.
  1000000000000    C00Lffffff0000       000      i00.              00000000             .::::.
             000   C00             0000000000    i00.              000                ::::,00000
  0000000000000f   C00                     000    0000000000000    00G000000000:   .::::     :0000L


Welcome you wonderful people of SpaceX.
    Here is a typical example of something I have written in Python.
    These examples were written for Python 2.X which I will assume you will be using for your projects.
    If you have bravely made the leap to Python 3.X I can provide examples in that version as well.
    Let me know if you would like to see more.
"""


import os
import time
import logging
from subprocess import Popen, PIPE
from datetime import datetime


class Result(object):

    def __init__(self):
        self.file_name = None
        self.directory = None
        self.succeeded = False
        self.full_path = None
        self.timestamp = None


class DataDecoder(object):
    """
    EXAMPLE 1:
    One day I was tasked with creating a single python wrapper for
    several tools used to pull data from a data collection board and
    save it to a file in a human readable format.
    """

    def __init__(self, board_ip, debug_file, output_dir, output_name):

        self.log = None
        self.board_ip = board_ip
        self.debug_file = debug_file
        self.output_dir = output_dir
        self.output_name = output_name

        t = time.time()
        self.raw_data_file = "/tmp/data_{0}.raw".format(t)
        self.decoded_data_file = "/tmp/data_{0}.decoded".format(t)

        self._configure_logging()
        self.results = Result()

    #--------------------------------------------------------------------------
    def stop(self):
        """stop recording data. returns True or False based on success."""
        self.log.info("stopping data board")
        cmd = "dataStop -a {0}".format(self.board_ip)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def start(self):
        """start recording data. returns True or False based on success."""
        self.log.info("starting data board")
        cmd = "dataStart -a {0}".format(self.board_ip)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def reset(self):
        """resets the data board. returns True or False based on success."""
        self.log.info("resetting data board")
        cmd = "dataReset -a {0}".format(self.board_ip)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def flush(self):
        """
        flushes the current buffer of data in the data board.
        returns True or False based on success.
        """
        self.log.info("flushing data buffer")
        cmd = "dataFlush -a {0}".format(self.board_ip)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def flush_and_start(self):
        """
        convenience method that combines flushing and then
        starting the board. returns True or False based on success.
        """
        flushed = self.flush()
        started = self.start()
        return flushed and started

    #--------------------------------------------------------------------------
    def initialize(self):
        """
        convenience method that resets, flushes, and starts the
        data board. returns True or False based on success.
        """
        a = self.reset()
        b = self.flush_and_start()
        return a and b

    #--------------------------------------------------------------------------
    def _dump(self):
        """
        pulls non-decoded data straight from the data board.
        returns True or False based on success.
        """
        self.log.info("pulling data from data board")
        cmd = "dataClient -o {0} -a {1}".format(self.raw_data_file, self.board_ip)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def _decode(self):
        """
        decode the data pulled from the data board, save the raw data to a
        temp file. returns True or False based on success.
        """
        self.log.info("decoding board data")
        cmd = "dataDecode -f {0} -o {1}".format(self.raw_data_file, self.decoded_data_file)
        reply = self._execute(cmd)
        return reply

    #--------------------------------------------------------------------------
    def _translate(self):
        """
        turn a raw decoded file into the final, human readable version.
        returns True or False based on success.
        """
        self.log.info("converting data data to human readable text")
        cmd = "decoder -d {0} -e {1} -o {2}"
        cmd = cmd.format(self.debug_file, self.decoded_data_file, self.output_name)
        reply = self._execute(cmd)

        if reply:
            # we decoded without error. verify data was captured.
            reply = self._verify_size()

        return reply

    #--------------------------------------------------------------------------
    def pull(self):
        """
        this method pulls a result from a data board, decodes it, verifies the
        data, and saves the data to a file in a human readable format. returns
        a Result object with our results as attributes.
        """

        self.log.info("pulling results")
        self.output_name = self._create_name()

        # execute these methods in order. if any method returns False, we've failed.
        for method in (self._dump, self._decode, self._translate):
            if not method():
                self.results.succeeded = False
                self._cleanup()
                break

        self.flush()
        return self.results
    
    #--------------------------------------------------------------------------
    def _verify_size(self):
        """
        verifies our successfully decoded result has data in it.
        if the file size is zero, i remove the empty file and temp file,
        then i return False. if file has data, then i just return True.
        """
        self.log.info("verifying data data was captured")

        if not os.path.getsize(self.output_name):
            self.log.error("no data in decoded result file")
            return False

        return True

    #--------------------------------------------------------------------------
    def _execute(self, cmd):
        """execute a command. returns True or False based on success."""

        p = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        stdout, stderr = p.communicate()

        if stderr:
            self.log.error("{0}".format(stderr))
            return False

        self.log.info(stdout)
        return True

    #--------------------------------------------------------------------------
    def _cleanup(self):
        """clean up by removing our temp files."""
        self.log.info("cleaning up data capture process")
        files = (self.raw_data_file, self.decoded_data_file, self.output_name)
        exist = [i for i in files if i]

        for f in exist:
            try:
                os.remove(f)
            except (IOError, OSError) as e:
                self.log.debug("couldn't remove temp file {0}".format(e))

    #--------------------------------------------------------------------------
    def _create_name(self):
        """
        create and return the name of our final result file.
        also apply some settings to our result class.
        """
        now = datetime.now()
        stamp = now.strftime("%H%M%S")
        name = "{0}_{1}_raw.result".format(self.output_name, stamp)
        path = os.path.join(self.output_dir, name)

        # add info to our result class
        self.results.file_name = name
        self.results.timestamp = now
        self.results.full_path = path
        self.results.directory = self.output_dir
        return path
    
    #--------------------------------------------------------------------------
    def _configure_logging(self):
        """
        if the user is running this class from the command
        line, then we want to set up logging to the console.
        otherwise, get the current logger.
        """

        self.log = logging.getLogger()

        if not self.log.handlers:
            handlers = [logging.StreamHandler(), ]
            logging.basicConfig(level=logging.DEBUG, handlers=handlers)


if __name__ == "__main__":

    # example usage
    decoder = DataDecoder("192.168.0.101", "/path/to/file", "/home", "penguin")
    results = decoder.pull()

    if results.succeeded:
        print("success! here's your data file: {0}".format(results.full_path))
    else:
        print("\n\nThis is just an example and doesn't really pull data from a board\n")

