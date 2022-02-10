# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from shotgun_desktop.qt import QtCore 
from shotgun_desktop.qt import QtGui 


from  . import resources_rc

class Ui_Splash(object):
    def setupUi(self, Splash):
        if not Splash.objectName():
            Splash.setObjectName(u"Splash")
        Splash.resize(512, 200)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Splash.sizePolicy().hasHeightForWidth())
        Splash.setSizePolicy(sizePolicy)
        Splash.setMinimumSize(QtCore.QSize(512, 200))
        Splash.setMaximumSize(QtCore.QSize(512, 200))
        Splash.setStyleSheet(u"QDialog\n"
"{\n"
"	border: 2px solid rgb(119, 134, 145)\n"
"}\n"
"\n"
"QWidget\n"
"{\n"
"    background-color:  rgb(36, 39, 42);\n"
"    color: rgb(198, 198, 198);\n"
"    font-size: 12px;\n"
"}")
        self.icon = QtGui.QLabel(Splash)
        self.icon.setObjectName(u"icon")
        self.icon.setGeometry(QtCore.QRect(16, 30, 480, 142))
        sizePolicy.setHeightForWidth(self.icon.sizePolicy().hasHeightForWidth())
        self.icon.setSizePolicy(sizePolicy)
        self.icon.setMinimumSize(QtCore.QSize(480, 142))
        self.icon.setMaximumSize(QtCore.QSize(480, 142))
        self.icon.setPixmap(QtGui.QPixmap(u":/res/splash.png"))
        self.icon.setScaledContents(True)
        self.message = QtGui.QLabel(Splash)
        self.message.setObjectName(u"message")
        self.message.setGeometry(QtCore.QRect(182, 146, 316, 31))
        self.message.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.version = QtGui.QLabel(Splash)
        self.version.setObjectName(u"version")
        self.version.setGeometry(QtCore.QRect(390, 40, 101, 20))
        self.version.setStyleSheet(u"color: rgb(104, 123, 135);")
        self.version.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

        self.retranslateUi(Splash)

        QtCore.QMetaObject.connectSlotsByName(Splash)
    # setupUi

    def retranslateUi(self, Splash):
        Splash.setWindowTitle(QtGui.QApplication.translate("Splash", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.icon.setText("")
        self.message.setText("")
        self.version.setText("")
    # retranslateUi

