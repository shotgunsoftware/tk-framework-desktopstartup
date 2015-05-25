# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

copyright = """# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""

import os
import json


# File that gets written when this code is bundled with the desktop installer.
# It usually points to the app_store.

LOCATION_YML_LOCATION = os.path.join(
    os.path.split(__file__)[0],
    "..",
    "..",
    "location.yml"
)


def get_location(sgtk, app_bootstrap):
    """
    Returns a location dictionary for the bundled framework.
    """
    # If the startup location had been overriden, the descriptor is automatically
    # a dev descriptor.
    if app_bootstrap.get_startup_location_override():
        return {
            "type": "dev",
            "path": app_bootstrap.get_startup_location_override()
        }

    # If we are running the bundled startup, it is possible to override it's
    # value on first run in order to trigger the system into pulling from
    # another location that the app_store, namely git. This is done through an
    # environment variable.
    if app_bootstrap.runs_bundled_startup() and "SGTK_DESKTOP_BUNDLED_DESCRIPTOR" in os.environ:
        json_data = json.loads(os.environ["SGTK_DESKTOP_BUNDLED_DESCRIPTOR"])
        desc = {}
        for k, v in json_data.iteritems():
            # Make the file more easily readable by removing unicode notation from
            # it.

            # Keys never need to be unicode.
            # However, path values need to be kept as is so that paths with non-ascii characters
            # still work.
            k = str(k)
            try:
                v = str(v)
            except UnicodeEncodeError:
                # This happens when the value can't be converted to a regular string, we'll
                # simply not convert it.
                pass

            desc[k] = v
        return desc

    # Read the location.yml file. Local import since sgtk is lazily loaded.
    from tank_vendor import yaml
    with open(LOCATION_YML_LOCATION, "r") as location_yml:
        location_data = yaml.load(location_yml) or {}
        return location_data.get("location")


def write_location(descriptor):
    """
    Returns a location dictionary for the bundled framework.
    """
    # Read the location.yml file. Local import since sgtk is lazily loaded.
    location_data = {
        "location": descriptor.get_location()
    }
    # Read the location.yml file. Local import since sgtk is lazily loaded.
    from tank_vendor import yaml
    old_umask = os.umask(0077)
    try:
        with open(os.path.join(descriptor.get_path(), "location.yml"), "w") as location_yml:
            location_yml.write(copyright)
            yaml.dump(location_data, location_yml)
    finally:
        os.umask(old_umask)
