# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from shotgun_desktop.qt import QtCore
for name, cls in QtCore.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls

from shotgun_desktop.qt import QtGui
for name, cls in QtGui.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls


from  . import resources_rc

class Ui_Splash(object):
    def setupUi(self, Splash):
        if not Splash.objectName():
            Splash.setObjectName(u"Splash")
        Splash.resize(600, 400)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Splash.sizePolicy().hasHeightForWidth())
        Splash.setSizePolicy(sizePolicy)
        Splash.setMinimumSize(QSize(600, 400))
        Splash.setMaximumSize(QSize(600, 400))
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
        self.icon = QLabel(Splash)
        self.icon.setObjectName(u"icon")
        self.icon.setEnabled(True)
        self.icon.setGeometry(QRect(5, 5, 590, 390))
        sizePolicy.setHeightForWidth(self.icon.sizePolicy().hasHeightForWidth())
        self.icon.setSizePolicy(sizePolicy)
        self.icon.setMinimumSize(QSize(590, 390))
        self.icon.setMaximumSize(QSize(590, 390))
        self.icon.setPixmap(QPixmap(u":/res/splash.png"))
        self.icon.setScaledContents(True)
        self.message = QLabel(Splash)
        self.message.setObjectName(u"message")
        self.message.setEnabled(False)
        self.message.setGeometry(QRect(20, 330, 561, 31))
        self.message.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"background-color: transparent")
        self.message.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.version = QLabel(Splash)
        self.version.setObjectName(u"version")
        self.version.setGeometry(QRect(460, 30, 121, 30))
        self.version.setStyleSheet(u"color: rgb(255, 255, 255);\n"
"background-color: rgb(0, 0, 0)")
        self.version.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.retranslateUi(Splash)

        QMetaObject.connectSlotsByName(Splash)
    # setupUi

    def retranslateUi(self, Splash):
        Splash.setWindowTitle(QCoreApplication.translate("Splash", u"Dialog", None))
        self.icon.setText("")
        self.message.setText("")
        self.version.setText("")
    # retranslateUi
