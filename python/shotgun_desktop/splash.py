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
from PySide import QtCore

from .ui import splash


class Splash(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.ui = splash.Ui_Splash()
        self.ui.setupUi(self)

        self.setWindowFlags(QtCore.Qt.SplashScreen)

    def set_message(self, text):
        self.ui.message.setText(text)
        QtGui.QApplication.instance().processEvents()

    def show(self):
        QtGui.QDialog.show(self)
        self.raise_()
        self.activateWindow()

    def hide(self):
        # There's no sense showing the previous message when we show the
        # splash next time.
        self.set_message("")
        QtGui.QDialog.hide(self)
