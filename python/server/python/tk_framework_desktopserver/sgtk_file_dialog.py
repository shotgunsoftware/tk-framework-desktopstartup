# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class SgtkFileDialog(QtGui.QFileDialog):
    """
    This is a QT file dialog that allows extended selection.
    Note that it doesn't quite succeed at this in every os as some can't do both file and folder extended selection.
    """

    _VOLUMES_URL = "file:///Volumes"

    def __init__(self, multi=False, *args, **kwargs):
        """
        Initialize file dialog.

        :param multi: Allow extended selection
        """
        QtGui.QFileDialog.__init__(self, *args, **kwargs)

        if multi:
            selection_mode = QtGui.QAbstractItemView.ExtendedSelection
        else:
            selection_mode = QtGui.QAbstractItemView.SingleSelection

        listview = self.findChild(QtGui.QListView, "listView")
        if listview:
            listview.setSelectionMode(selection_mode)

        treeview = self.findChild(QtGui.QTreeView)
        if treeview:
            treeview.setSelectionMode(selection_mode)

        # FIXME: On MacOS the QFileDialog hides all hidden files. Unfortunately /Volumes is hidden.
        # As a quick hack to unblock our clients, we'll add /Volumes to the sidebar.
        if sys.platform == "darwin":
            sidebar_urls = self.sidebarUrls()
            if self._VOLUMES_URL not in sidebar_urls:
                sidebar_urls.append(self._VOLUMES_URL)
            self.setSidebarUrls(sidebar_urls)

        # Make the combobox editable so we can specify a path through it.
        c = self.findChild(QtGui.QComboBox, "lookInCombo")
        c.setEditable(True)
        # Search for the line edit widget, it has no name so scan for it.
        line_edits = filter(lambda x: isinstance(x, QtGui.QLineEdit), c.children())
        if len(line_edits) != 1:
            raise Exception("Expected to find a line edit widget.")
        self._path_editor = line_edits[0]
        # When the user presses return, we'll move to that directory.
        self._path_editor.returnPressed.connect(self._path_confirmed)

    def _path_confirmed(self):
        """
        When the user presses RETURN in the combo box, we update the current directory to the
        path specified in the combo box.
        """
        self.setDirectory(self._path_editor.text())

    def exec_(self):
        """
        Shows the window modally and in the foreground.

        :returns: The return code specified by the call to quit().
        """
        self.show()
        self.raise_()
        self.activateWindow()

        # the trick of activating + raising does not seem to be enough for
        # modal dialogs. So force put them on top as well.
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
        return QtGui.QDialog.exec_(self)

    def accept(self, *args, **kwargs):
        """
        Override method for accept button. Allows to emit an event with the list of selected files.
        """
        files = self.selectedFiles()
        if len(files) == 0:
            return

        self.fileSelected.emit(files)
        QtGui.QDialog.accept(self, *args, **kwargs)
