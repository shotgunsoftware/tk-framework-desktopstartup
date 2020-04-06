# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'splash.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from shotgun_desktop.qt import QtCore, QtGui

class Ui_Splash(object):
    def setupUi(self, Splash):
        Splash.setObjectName("Splash")
        Splash.resize(512, 200)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Splash.sizePolicy().hasHeightForWidth())
        Splash.setSizePolicy(sizePolicy)
        Splash.setMinimumSize(QtCore.QSize(512, 200))
        Splash.setMaximumSize(QtCore.QSize(512, 200))
        Splash.setStyleSheet("QDialog\n"
"{\n"
"    border: 2px solid rgb(119, 134, 145)\n"
"}\n"
"\n"
"QWidget\n"
"{\n"
"    background-color:  rgb(36, 39, 42);\n"
"    color: rgb(198, 198, 198);\n"
"    font-size: 12px;\n"
"}")
        self.icon = QtGui.QLabel(Splash)
        self.icon.setGeometry(QtCore.QRect(16, 30, 480, 142))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.icon.sizePolicy().hasHeightForWidth())
        self.icon.setSizePolicy(sizePolicy)
        self.icon.setMinimumSize(QtCore.QSize(480, 142))
        self.icon.setMaximumSize(QtCore.QSize(480, 142))
        self.icon.setText("")
        self.icon.setPixmap(QtGui.QPixmap(":/res/splash.png"))
        self.icon.setScaledContents(True)
        self.icon.setObjectName("icon")
        self.message = QtGui.QLabel(Splash)
        self.message.setGeometry(QtCore.QRect(182, 146, 316, 31))
        self.message.setText("")
        self.message.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.message.setObjectName("message")

        self.retranslateUi(Splash)
        QtCore.QMetaObject.connectSlotsByName(Splash)

    def retranslateUi(self, Splash):
        Splash.setWindowTitle(QtGui.QApplication.translate("Splash", "Dialog", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
