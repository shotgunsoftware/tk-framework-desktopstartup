# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from PySide import QtCore, QtGui
import sys


class ShotgunSystemTrayIcon(QtGui.QSystemTrayIcon):
    """
    Shows a systray icon with Login, About and Quit.
    """
    login = QtCore.Signal()
    quit = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Constructor.
        """
        QtGui.QSystemTrayIcon.__init__(self, parent)

        # configure the system tray icon
        icon = QtGui.QIcon(":/res/shotgun_badge")
        self.setIcon(icon)
        self.setToolTip("Shotgun")

        # Create the pop-up menu.
        self._systray_menu = QtGui.QMenu()
        self._login_action = self._systray_menu.addAction("Sign in to Shotgun Desktop")
        self._about_action = self._systray_menu.addAction("About Browser Integration")
        self._systray_menu.addSeparator()
        self._quit_action = self._systray_menu.addAction("Quit")

        # connect up signal handlers
        self._login_action.triggered.connect(self.login)
        self._about_action.triggered.connect(self._about)
        self._quit_action.triggered.connect(self.quit)

        # On MacOS, the context menu is more than a pop-up menu and shows up on the
        # mouse click, so setting it as context menu makes sense.
        if sys.platform == "darwin":
            self.setContextMenu(self._systray_menu)
        else:
            # On Windows and Linux, they are glorified pop-up menus that appear on a right
            # click, but we want our menu to appear on any click, so connect to the activated
            # event.
            self.activated.connect(self._activated)

    def _activated(self, unused):
        """
        Called when the systray icon is activated.
        """
        # Don't care how it is activated for now, just show the menu.
        self._systray_menu.exec_(QtGui.QCursor.pos())

    def _about(self):
        """
        When About is selected, launch the Shotgun browser integration support page.
        """
        QtGui.QDesktopServices.openUrl("https://support.shotgunsoftware.com/entries/95402178")
