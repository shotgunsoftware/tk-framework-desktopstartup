# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .qt import QtCore, QtGui


class DesktopMessageBox(QtGui.QMessageBox):
    @staticmethod
    def critical(
        title,
        message,
        default_button=QtGui.QMessageBox.Ok,
        buttons=QtGui.QMessageBox.Ok,
        detailed_text=None,
        parent=None,
    ):
        """
        Pops a critical message box, very similar to QtGui.QMessageBox.critical.

        :param title: Text to display in the title bar.
        :param message: Text to display in the body of the dialog. Text is split into a separate
            paragraph after each \n.
        :param default_button: Button that will be highlighted bu default. Defaults to
            QtGui.QMessageBox.Ok
        :param buttons: Union of QtGui.QMessageBox.StandardButton to display in the dialog. Defaults
            to QtGui.QMessageBox.Ok
        :param detailed_text: Text to display in the detailed area when clicking "Show Details...".
            If None, the button won't be displayed.
        :param parent: Parent widget of this message box.

        :returns: The QtGui.QMessageBox.StandardButton value representing the user selection.
        """
        return DesktopMessageBox(
            QtGui.QMessageBox.Critical,
            title,
            message,
            default_button,
            buttons,
            detailed_text,
            parent,
        ).exec_()

    @staticmethod
    def information(
        title,
        message,
        default_button=QtGui.QMessageBox.Ok,
        buttons=QtGui.QMessageBox.Ok,
        detailed_text=None,
        parent=None,
    ):
        """
        Pops an informational message box, very similar to QtGui.QMessageBox.information.

        :param title: Text to display in the title bar.
        :param message: Text to display in the body of the dialog. Text is split into a separate
            paragraph after each \n.
        :param default_button: Button that will be highlighted bu default. Defaults to
            QtGui.QMessageBox.Ok
        :param buttons: Union of QtGui.QMessageBox.StandardButton to display in the dialog. Defaults
            to QtGui.QMessageBox.Ok
        :param detailed_text: Text to display in the detailed area when clicking "Show Details...".
            If None, the button won't be displayed.
        :param parent: Parent widget of this message box.

        :returns: The QtGui.QMessageBox.StandardButton value representing the user selection.
        """
        return DesktopMessageBox(
            QtGui.QMessageBox.Information,
            title,
            message,
            default_button,
            buttons,
            detailed_text,
            parent,
        ).exec_()

    @staticmethod
    def warning(
        title,
        message,
        default_button=QtGui.QMessageBox.Ok,
        buttons=QtGui.QMessageBox.Ok,
        detailed_text=None,
        parent=None,
    ):
        """
        Pops a warning message box, very similar to QtGui.QMessageBox.warning.

        :param title: Text to display in the title bar.
        :param message: Text to display in the body of the dialog. Text is split into a separate
            paragraph after each \n.
        :param default_button: Button that will be highlighted bu default. Defaults to
            QtGui.QMessageBox.Ok
        :param buttons: Union of QtGui.QMessageBox.StandardButton to display in the dialog. Defaults
            to QtGui.QMessageBox.Ok
        :param detailed_text: Text to display in the detailed area when clicking "Show Details...".
            If None, the button won't be displayed.
        :param parent: Parent widget of this message box.

        :returns: The QtGui.QMessageBox.StandardButton value representing the user selection.
        """
        return DesktopMessageBox(
            QtGui.QMessageBox.Warning,
            title,
            message,
            default_button,
            buttons,
            detailed_text,
            parent,
        ).exec_()

    def __init__(
        self,
        icon,
        title,
        message,
        default_button,
        buttons,
        detailed_text=None,
        parent=None,
    ):
        """
        Pops a warning message box, very similar to QtGui.QMessageBox.warning.

        :param icon: QtGui.QMessageBox.Icon value representing the icon to display.
        :param title: Text to display in the title bar.
        :param message: Text to display in the body of the dialog. Text is split into a separate
            paragraph after each \n.
        :param default_button: Button that will be highlighted bu default. Defaults to
            QtGui.QMessageBox.Ok
        :param buttons: Union of QtGui.QMessageBox.StandardButton to display in the dialog. Defaults
            to QtGui.QMessageBox.Ok
        :param detailed_text: Text to display in the detailed area when clicking "Show Details...".
            If None, the button won't be displayed.
        :param parent: Parent widget of this message box.

        :returns: The QtGui.QMessageBox.StandardButton value representing the user selection.
        """

        QtGui.QMessageBox.__init__(self)

        # Retrieve the style to get the message box icon associated to it. Icon is a temporary
        # object.
        self.setStyleSheet(
            """QWidget
            {
                background-color:  rgb(36, 39, 42);
                color: rgb(192, 193, 195);
                selection-background-color: rgb(168, 123, 43);
                selection-color: rgb(230, 230, 230);
                font-size: 11px;
                color: rgb(192, 192, 192);
            }

            QPushButton
            {
                background-color: transparent;
                border-radius: 2px;
                padding: 8px;
                padding-left: 15px;
                padding-right: 15px;
            }

            QPushButton:default
            {
                color: rgb(248, 248, 248);
                background-color: rgb(35, 165, 225);
            }
            """
        )
        # Set the requested icon
        self.setIcon(icon)

        # Set the buttons
        self.setStandardButtons(buttons)
        self.setDefaultButton(default_button)

        if detailed_text:
            self.setDetailedText(detailed_text)

        # Set the title
        self.setWindowTitle(title)

        # Create a paragraph per \n line of text.
        message = "".join(
            [
                '<p><span style=" font-size:12pt;">%s</span></p>' % para
                for para in message.split("\n")
            ]
        )
        self.setText(
            """
            <html>
                <head>
                    <style>
                        a {color: rgb(35,165,225)}
                    </style>
                </head>
                <body>%s</body>
            </html>"""
            % message
        )

    def exec_(self):
        """
        Displays the window modally and makes sure it goes front and center.
        """
        self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
        return QtGui.QDialog.exec_(self)
