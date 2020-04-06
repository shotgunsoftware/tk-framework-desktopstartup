# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .qt import QtGui

from .ui import turn_on_toolkit


class TurnOnToolkit(QtGui.QDialog):
    def __init__(self, connection, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.ui = turn_on_toolkit.Ui_TurnOnToolkit()
        self.ui.setupUi(self)

        url_text = (
            "<a href='%s/page/manage_apps'>"
            "<span style='font-size:20pt; text-decoration: underline; color:#f0f0f0;'>"
            "Manage Apps</span></a>" % connection.base_url
        )
        self.ui.url_label.setText(url_text)
