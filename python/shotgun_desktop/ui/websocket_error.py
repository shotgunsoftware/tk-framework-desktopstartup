# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'websocket_error.ui'
#
# Created: Wed Sep 23 22:50:08 2015
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_WebsocketError(object):
    def setupUi(self, WebsocketError):
        WebsocketError.setObjectName("WebsocketError")
        WebsocketError.resize(373, 135)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(WebsocketError.sizePolicy().hasHeightForWidth())
        WebsocketError.setSizePolicy(sizePolicy)
        WebsocketError.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        WebsocketError.setStyleSheet("QWidget\n"
"{\n"
"    background-color:  rgb(36, 39, 42);\n"
"    color: rgb(192, 193, 195);\n"
"    selection-background-color: rgb(168, 123, 43);\n"
"    selection-color: rgb(230, 230, 230);\n"
"    font-size: 11px;\n"
"    color: rgb(192, 192, 192);\n"
"}\n"
"\n"
"QPushButton\n"
"{\n"
"    background-color: transparent;\n"
"    border-radius: 2px;\n"
"    padding: 8px;\n"
"    padding-left: 15px;\n"
"    padding-right: 15px;\n"
"}\n"
"\n"
"QLineEdit\n"
"{\n"
"    background-color: rgb(29, 31, 34);\n"
"    border: 1px solid rgb(54, 60, 66);\n"
"    border-radius: 2px;\n"
"    padding: 5px;\n"
"    font-size: 12px;\n"
"}\n"
"\n"
"QLineEdit:focus\n"
"{\n"
"    border: 1px solid rgb(48, 167, 227);\n"
"}\n"
"\n"
"QLineEdit:Disabled {\n"
"    background-color: rgb(60, 60, 60);\n"
"    color: rgb(160, 160, 160);\n"
"}")
        self.verticalLayout = QtGui.QVBoxLayout(WebsocketError)
        self.verticalLayout.setContentsMargins(20, 20, 20, 20)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_frame = QtGui.QFrame(WebsocketError)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_frame.sizePolicy().hasHeightForWidth())
        self.label_frame.setSizePolicy(sizePolicy)
        self.label_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.label_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.label_frame.setObjectName("label_frame")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.label_frame)
        self.horizontalLayout_2.setSpacing(20)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.icon = QtGui.QLabel(self.label_frame)
        self.icon.setText("")
        self.icon.setAlignment(QtCore.Qt.AlignCenter)
        self.icon.setObjectName("icon")
        self.horizontalLayout_2.addWidget(self.icon)
        self.widget = QtGui.QWidget(self.label_frame)
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.widget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.heading = QtGui.QLabel(self.widget)
        self.heading.setObjectName("heading")
        self.verticalLayout_2.addWidget(self.heading)
        self.error = QtGui.QLabel(self.widget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.error.sizePolicy().hasHeightForWidth())
        self.error.setSizePolicy(sizePolicy)
        self.error.setObjectName("error")
        self.verticalLayout_2.addWidget(self.error)
        self.question = QtGui.QLabel(self.widget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.question.sizePolicy().hasHeightForWidth())
        self.question.setSizePolicy(sizePolicy)
        self.question.setWordWrap(True)
        self.question.setObjectName("question")
        self.verticalLayout_2.addWidget(self.question)
        self.horizontalLayout_2.addWidget(self.widget)
        self.verticalLayout.addWidget(self.label_frame)
        self.button_frame = QtGui.QFrame(WebsocketError)
        self.button_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.button_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.button_frame.setObjectName("button_frame")
        self.horizontalLayout = QtGui.QHBoxLayout(self.button_frame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.no_button = QtGui.QPushButton(self.button_frame)
        self.no_button.setFlat(True)
        self.no_button.setObjectName("no_button")
        self.horizontalLayout.addWidget(self.no_button)
        self.ok_button = QtGui.QPushButton(self.button_frame)
        self.ok_button.setStyleSheet("background-color: rgb(16, 148,223);")
        self.ok_button.setDefault(True)
        self.ok_button.setFlat(True)
        self.ok_button.setObjectName("ok_button")
        self.horizontalLayout.addWidget(self.ok_button)
        self.verticalLayout.addWidget(self.button_frame)
        self.actionClear_login_data = QtGui.QAction(WebsocketError)
        self.actionClear_login_data.setObjectName("actionClear_login_data")

        self.retranslateUi(WebsocketError)
        QtCore.QObject.connect(self.no_button, QtCore.SIGNAL("clicked()"), WebsocketError.reject)
        QtCore.QObject.connect(self.ok_button, QtCore.SIGNAL("clicked()"), WebsocketError.accept)
        QtCore.QMetaObject.connectSlotsByName(WebsocketError)

    def retranslateUi(self, WebsocketError):
        WebsocketError.setWindowTitle(QtGui.QApplication.translate("WebsocketError", "Browser integration error", None, QtGui.QApplication.UnicodeUTF8))
        self.heading.setText(QtGui.QApplication.translate("WebsocketError", "<html><head/><body><p><span style=\" font-size:12pt;\">Browser integration failed to initialize properly:</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.error.setText(QtGui.QApplication.translate("WebsocketError", "<html><head/><body><p><span style=\" font-size:12pt;\">TextLabel</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.question.setText(QtGui.QApplication.translate("WebsocketError", "<html><head/><body><p><span style=\" font-size:12pt;\">Continue launching without browser integration?</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.no_button.setText(QtGui.QApplication.translate("WebsocketError", "No", None, QtGui.QApplication.UnicodeUTF8))
        self.ok_button.setText(QtGui.QApplication.translate("WebsocketError", "Yes", None, QtGui.QApplication.UnicodeUTF8))
        self.actionClear_login_data.setText(QtGui.QApplication.translate("WebsocketError", "Clear login data", None, QtGui.QApplication.UnicodeUTF8))
        self.actionClear_login_data.setToolTip(QtGui.QApplication.translate("WebsocketError", "Clear all the cached login data, including site, login, and password.", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
