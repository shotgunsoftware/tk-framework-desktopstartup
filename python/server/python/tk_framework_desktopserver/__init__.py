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
import sys

python_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../resources/python"))
sys.path.append(os.path.join(python_path, "common"))

distributions_path = os.path.join(python_path, "dist")
if sys.platform.startswith("darwin"):
    sys.path.append(os.path.join(distributions_path, "mac"))
elif os.name == "nt":
    sys.path.append(os.path.join(distributions_path, "win"))
elif os.name == "posix":
    sys.path.append(os.path.join(distributions_path, "linux"))

from .server import Server
from .process_manager import ProcessManager
from .certificates import get_certificate_handler
from .logger import get_logger
