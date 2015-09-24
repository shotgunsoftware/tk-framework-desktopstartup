# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from PySide import QtGui

from .ui import websocket_error


class WebsocketError(QtGui.QDialog):
    def __init__(self, error_message, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.ui = websocket_error.Ui_WebsocketError()
        self.ui.setupUi(self)

        # Retrieve the style to get the message box icon associated to it. Icon is a temporary
        # object.
        icon = self.style().standardIcon(QtGui.QStyle.SP_MessageBoxWarning, None, self)

        # Ask for the size of the icon.
        icon_size = self.style().pixelMetric(QtGui.QStyle.PM_MessageBoxIconSize, None, self)

        # Create the pixmap and set it on the icon label. We own the pixmap.
        self._pixmap = icon.pixmap(icon_size, icon_size)
        self.ui.icon.setPixmap(self._pixmap)

        self.ui.error.setText(
            "<html><head/><body><p><span style=\" font-size:12pt;\">%s</span></p></body></html>" %
            str(error_message).strip()
        )
