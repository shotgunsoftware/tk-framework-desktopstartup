# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import subprocess
from threading import Thread
from Queue import Queue
import sys


class ReadThread(Thread):
    def __init__(self, p_out, target_queue):
        Thread.__init__(self)
        self.pipe = p_out
        self.target_queue = target_queue

    def run(self):
        while True:
            line = self.pipe.readline()         # blocking read
            if line == '':
                break
            self.target_queue.put(line)


class Command(object):

    @staticmethod
    def _enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    @staticmethod
    def call_cmd(args):
        # Note: Tie stdin to a PIPE as well to avoid this python bug on windows
        # http://bugs.python.org/issue3905
        # Queue code taken from: http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        stdout_lines = []
        stderr_lines = []
        try:
            # Prevents the cmd.exe dialog from appearing on Windows.
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            else:
                startupinfo = None

            # The commands that are being run are probably being launched from Desktop, which would
            # have a TANK_CURRENT_PC environment variable set to the site configuration. Since we
            # preserve that value for subprocesses (which is usually the behavior we want), the DCCs
            # being launched would try to run in the project environment and would get an error due
            # to the conflict.
            #
            # Clean up the environment to prevent that from happening.
            env = os.environ.copy()
            vars_to_remove = ["TANK_CURRENT_PC"]
            for var in vars_to_remove:
                if var in env:
                    del env[var]

            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                env=env,
            )
            process.stdin.close()

            stdout_q = Queue()
            stderr_q = Queue()

            stdout_t = ReadThread(process.stdout, stdout_q)
            stdout_t.setDaemon(True)
            stdout_t.start()

            stderr_t = ReadThread(process.stderr, stderr_q)
            stderr_t.setDaemon(True)
            stderr_t.start()

            # Popen.communicate() doesn't play nicely if the stdin pipe is closed
            # as it tries to flush it causing an 'I/O error on closed file' error
            # when run from a terminal
            #
            # to avoid this, lets just poll the output from the process until
            # it's finished
            process.wait()

            process.stdout.flush()
            process.stderr.flush()
            stdout_t.join()
            stderr_t.join()

            while not stdout_q.empty():
                stdout_lines.append(stdout_q.get())

            while not stderr_q.empty():
                stderr_lines.append(stderr_q.get())

            ret = process.returncode
        except StandardError:
            import traceback
            ret = 1
            stderr_lines = traceback.format_exc().split()
            stderr_lines.append("%s" % args)

        out = ''.join(stdout_lines)
        err = ''.join(stderr_lines)

        return ret, out, err
