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


def _get_location_yaml_location(root):
    """
    Computes the path to the location.yml file.

    :param root: Path pointing to the root of a bundle.

    :returns: A string pointing to root/resources/location.yml
    """
    return os.path.join(
        root,
        "resources",
        "location.yml"
    )


def get_location(sgtk, app_bootstrap):
    """
    Returns a location dictionary for the bundled framework.

    :param sgtk: Handle to the Toolkit API
    :param app_bootstrap: Instance of the application bootstrap.

    :returns: A dictionary with keys and values following the Toolkit location
        convention. Read more at https://toolkit.shotgunsoftware.com/entries/23797786#Code%20Locations
    """
    dev_descriptor = {
        "type": "dev",
        "path": app_bootstrap.get_startup_location_override()
    }
    # If the startup location had been overriden, the descriptor is automatically
    # a dev descriptor.
    if app_bootstrap.get_startup_location_override():
        return dev_descriptor

    # If we are running the bundled startup, it is possible to override it's
    # value on first run in order to trigger the system into pulling from
    # another location that the app_store, namely git. This is done through an
    # environment variable. This is also great for testing app_store updates
    # by pretending you have an older version of the code bundled and need an update.
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

    location = _get_location_yaml_location(app_bootstrap.get_startup_path())

    # If the file is missing, we're in dev mode.
    if not os.path.exists(location):
        return dev_descriptor

    # Read the location.yml file. Local import since sgtk is lazily loaded.
    from tank_vendor import yaml
    with open(location, "r") as location_file:
        # If the file is empty, we're in dev mode.
        return yaml.load(location_file) or dev_descriptor


def write_location(descriptor):
    """
    Writes the descriptor dictionary to disk in the BUNDLE_ROOT/resources/location.yml file.
    """
    # Local import since sgtk is lazily loaded.
    from tank_vendor import yaml
    old_umask = os.umask(0077)
    try:
        # Write the toolkit descriptor information to disk.
        location_yml_path = os.path.join(_get_location_yaml_location(descriptor.get_path()))
        with open(location_yml_path, "w") as location_yml:
            location_yml.write(copyright)
            yaml.dump(descriptor.get_location(), location_yml)
    finally:
        os.umask(old_umask)
