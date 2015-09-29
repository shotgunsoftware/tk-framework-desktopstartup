# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'additional_details.ui'
#
# Created: Thu May 14 23:57:57 2015
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(514, 255)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/res/sg_badge"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog.setWindowIcon(icon)
        Dialog.setStyleSheet("QWidget\n"
"{\n"
"    background-color:  rgb(43, 46, 48);\n"
"    color: rgb(185, 185, 185);\n"
"    border-radius: 2px;\n"
"    selection-background-color: rgb(167, 167, 167);\n"
"    selection-color: rgb(26, 26, 26);\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton\n"
"{\n"
"    background-color: rgb(83, 83, 83);\n"
"    border: none;\n"
"    padding: 5px;\n"
"    padding-left: 15px;\n"
"    padding-right: 15px;\n"
"}\n"
"\n"
"QPushButton:focus\n"
"{\n"
"    border: 1px solid rgb(185, 185, 185);\n"
"}\n"
"\n"
"QLineEdit\n"
"{\n"
"    border: 1px solid rgb(180, 180, 180);\n"
"    padding: 5px;\n"
"}")
        self.gridLayout = QtGui.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.install = QtGui.QLineEdit(Dialog)
        self.install.setObjectName("install")
        self.gridLayout.addWidget(self.install, 2, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 3)
        self.label = QtGui.QLabel(Dialog)
        self.label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)
        self.label_2 = QtGui.QLabel(Dialog)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 3)
        self.browse = QtGui.QPushButton(Dialog)
        self.browse.setFlat(True)
        self.browse.setObjectName("browse")
        self.gridLayout.addWidget(self.browse, 2, 2, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.defaults = QtGui.QPushButton(Dialog)
        self.defaults.setFlat(True)
        self.defaults.setObjectName("defaults")
        self.horizontalLayout.addWidget(self.defaults)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.cancel = QtGui.QPushButton(Dialog)
        self.cancel.setFlat(True)
        self.cancel.setObjectName("cancel")
        self.horizontalLayout.addWidget(self.cancel)
        self.ok = QtGui.QPushButton(Dialog)
        self.ok.setDefault(True)
        self.ok.setFlat(True)
        self.ok.setObjectName("ok")
        self.horizontalLayout.addWidget(self.ok)
        self.gridLayout.addLayout(self.horizontalLayout, 5, 0, 1, 3)
        spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 4, 0, 1, 3)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.cancel, QtCore.SIGNAL("clicked()"), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.install, self.browse)
        Dialog.setTabOrder(self.browse, self.defaults)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Toolkit Information", None, QtGui.QApplication.UnicodeUTF8))
        self.install.setPlaceholderText(QtGui.QApplication.translate("Dialog", "/path/to/toolkit/install", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "<html><head/><body><p align=\"center\"><span style=\" font-size:large;\">Looks like you already have Toolkit setup.</span></p><p>If you want to keep using your current toolkit install, enter the path to it below. If the path points to an existing install, then it will be used. If it doesn\'t, then a new Toolkit install will be set up at that location.</p><p>In addition a new Pipeline Configuration will be set up for a site wide environment. This configuration will be set up in the Data directory next to the Desktop application.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Dialog", "<html><head/><body><p>* Note: A project will be created under your projects folder named &quot;site&quot;.  Cancel to avoid this. </p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.browse.setText(QtGui.QApplication.translate("Dialog", "Browse...", None, QtGui.QApplication.UnicodeUTF8))
        self.defaults.setText(QtGui.QApplication.translate("Dialog", "Reset to Default", None, QtGui.QApplication.UnicodeUTF8))
        self.cancel.setText(QtGui.QApplication.translate("Dialog", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.ok.setText(QtGui.QApplication.translate("Dialog", "Ok", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
