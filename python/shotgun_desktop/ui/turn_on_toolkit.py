# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'turn_on_toolkit.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from shotgun_desktop.qt import QtCore, QtGui

class Ui_TurnOnToolkit(object):
    def setupUi(self, TurnOnToolkit):
        TurnOnToolkit.setObjectName("TurnOnToolkit")
        TurnOnToolkit.resize(443, 423)
        TurnOnToolkit.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        TurnOnToolkit.setStyleSheet("QWidget\n"
"{\n"
"    background-color:  rgb(36, 39, 42);\n"
"    color: rgb(240, 240, 240);\n"
"    selection-background-color: rgb(167, 167, 167);\n"
"    selection-color: rgb(26, 26, 26);\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton\n"
"{\n"
"    background-color: rgb(83, 83, 83);\n"
"    border: 1px solid black;\n"
"    border-radius: 2px;\n"
"    padding: 5px;\n"
"    padding-left: 35px;\n"
"    padding-right: 35px;\n"
"}\n"
"\n"
"QPushButton:focus\n"
"{\n"
"    border: 1px solid rgb(185, 185, 185);\n"
"}\n"
"\n"
"QLineEdit\n"
"{\n"
"    background-color: rgb(42, 42, 42);\n"
"    border: 1px solid black;\n"
"    border-radius: 2px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QLineEdit:focus\n"
"{\n"
"    border: 1px solid rgb(48, 167, 227);\n"
"}")
        self.verticalLayout = QtGui.QVBoxLayout(TurnOnToolkit)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_frame = QtGui.QFrame(TurnOnToolkit)
        self.label_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.label_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.label_frame.setObjectName("label_frame")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.label_frame)
        self.verticalLayout_2.setSpacing(30)
        self.verticalLayout_2.setContentsMargins(20, 20, 20, -1)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.static_label = QtGui.QLabel(self.label_frame)
        self.static_label.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignHCenter)
        self.static_label.setWordWrap(True)
        self.static_label.setObjectName("static_label")
        self.verticalLayout_2.addWidget(self.static_label)
        self.url_label = QtGui.QLabel(self.label_frame)
        self.url_label.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
        self.url_label.setOpenExternalLinks(True)
        self.url_label.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)
        self.url_label.setObjectName("url_label")
        self.verticalLayout_2.addWidget(self.url_label)
        self.note_label = QtGui.QLabel(self.label_frame)
        self.note_label.setAlignment(QtCore.Qt.AlignBottom|QtCore.Qt.AlignHCenter)
        self.note_label.setObjectName("note_label")
        self.verticalLayout_2.addWidget(self.note_label)
        self.verticalLayout_2.setStretch(0, 1)
        self.verticalLayout_2.setStretch(2, 1)
        self.verticalLayout.addWidget(self.label_frame)
        self.button_frame = QtGui.QFrame(TurnOnToolkit)
        self.button_frame.setStyleSheet("QFrame {\n"
"    background-color: rgb(30, 30, 30);\n"
"}")
        self.button_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.button_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.button_frame.setObjectName("button_frame")
        self.horizontalLayout = QtGui.QHBoxLayout(self.button_frame)
        self.horizontalLayout.setSpacing(-1)
        self.horizontalLayout.setContentsMargins(20, 20, 20, 20)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.cancel_button = QtGui.QPushButton(self.button_frame)
        self.cancel_button.setFlat(True)
        self.cancel_button.setObjectName("cancel_button")
        self.horizontalLayout.addWidget(self.cancel_button)
        self.retry_button = QtGui.QPushButton(self.button_frame)
        self.retry_button.setStyleSheet("background-color: rgb(16, 148,223);")
        self.retry_button.setDefault(True)
        self.retry_button.setFlat(True)
        self.retry_button.setObjectName("retry_button")
        self.horizontalLayout.addWidget(self.retry_button)
        self.horizontalLayout.setStretch(0, 1)
        self.verticalLayout.addWidget(self.button_frame)
        self.verticalLayout.setStretch(0, 1)
        self.actionClear_login_data = QtGui.QAction(TurnOnToolkit)
        self.actionClear_login_data.setObjectName("actionClear_login_data")

        self.retranslateUi(TurnOnToolkit)
        QtCore.QObject.connect(self.cancel_button, QtCore.SIGNAL("clicked()"), TurnOnToolkit.reject)
        QtCore.QObject.connect(self.retry_button, QtCore.SIGNAL("clicked()"), TurnOnToolkit.accept)
        QtCore.QMetaObject.connectSlotsByName(TurnOnToolkit)

    def retranslateUi(self, TurnOnToolkit):
        TurnOnToolkit.setWindowTitle(QtGui.QApplication.translate("TurnOnToolkit", "Turn on Toolkit", None, QtGui.QApplication.UnicodeUTF8))
        self.static_label.setText(QtGui.QApplication.translate("TurnOnToolkit", "<html><head/><body><p><span style=\" font-size:28pt;\">Toolkit must be enabled in Shotgun to proceed with installation.</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.url_label.setText(QtGui.QApplication.translate("TurnOnToolkit", "<a href=\"foo\"><span style=\" font-size:20pt; text-decoration: underline; color:#f0f0f0;\">Turn it on in Manage Apps.</span></a>", None, QtGui.QApplication.UnicodeUTF8))
        self.note_label.setText(QtGui.QApplication.translate("TurnOnToolkit", "* Note: You must log in as an admin to be able to turn on Toolkit.", None, QtGui.QApplication.UnicodeUTF8))
        self.cancel_button.setText(QtGui.QApplication.translate("TurnOnToolkit", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.retry_button.setText(QtGui.QApplication.translate("TurnOnToolkit", "Retry", None, QtGui.QApplication.UnicodeUTF8))
        self.actionClear_login_data.setText(QtGui.QApplication.translate("TurnOnToolkit", "Clear login data", None, QtGui.QApplication.UnicodeUTF8))
        self.actionClear_login_data.setToolTip(QtGui.QApplication.translate("TurnOnToolkit", "Clear all the cached login data, including site, login, and password.", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
