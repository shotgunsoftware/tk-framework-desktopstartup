# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .qt import QtGui, QtCore

from .ui import splash


class Splash(QtGui.QDialog):
    """
    Splash screen with customizable message shown during the application startup.
    """

    def __init__(self, parent=None):
        """
        Constructor. Widget is initially hidden.
        """
        QtGui.QDialog.__init__(self, parent)

        self.ui = splash.Ui_Splash()
        self.ui.setupUi(self)

        self.setWindowFlags(QtCore.Qt.SplashScreen)

    def set_message(self, text):
        """
        Sets the message to display on the widget.

        :param text: Text to display.
        """
        self.ui.message.setText(text)
        QtGui.QApplication.instance().processEvents()

    def show(self):
        """
        Shows the dialog of top of all other dialogs.
        """
        QtGui.QDialog.show(self)
        self.raise_()
        self.activateWindow()

    def hide(self):
        """
        Hides the dialog and clears the current message.
        """
        # There's no sense showing the previous message when we show the
        # splash next time.
        self.set_message("")
        QtGui.QDialog.hide(self)
