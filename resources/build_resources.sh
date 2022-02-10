#!/usr/bin/env bash
#
# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# The path to output all built .py files to:
UI_PYTHON_PATH=../python/shotgun_desktop/ui

function build_qt {
    echo " > Building " $2

    # compile ui to python
    $1 $2 > $UI_PYTHON_PATH/$3.py

    sed -i $UI_PYTHON_PATH/$3.py -e "s/from PySide2 import/from shotgun_desktop.qt import/g"  -e "/# Created:/d"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/from PySide2\./from shotgun_desktop.qt import /g" -e "/# Created:/d"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/ import \*/ /g"  -e "/# Created:/d"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/from shotgun_desktop.qt import QtWidgets //g"  -e "/# Created:/d"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QSizePolicy/QtGui\.QSizePolicy/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QSize(/QtCore.QSize(/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QLabel(/QtGui.QLabel(/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QRect(/QtCore.QRect(/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/Qt\.Align/QtCore\.Qt\.Align/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QMetaObject/QtCore\.QMetaObject/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/QPixmap/QtGui\.QPixmap/g"
    sed -i $UI_PYTHON_PATH/$3.py -e "s/Splash\.setWindowTitle(QCoreApplication\.translate(\"Splash\", u\"Dialog\", None))/Splash\.setWindowTitle(QtGui\.QApplication\.translate(\"Splash\", \"Dialog\", None, QtGui\.QApplication\.UnicodeUTF8))/g"
}

function build_ui {
    build_qt "pyside2-uic --from-imports" "$1.ui" "$1"
}

function build_res {
    build_qt "pyside2-rcc -g python" "$1.qrc" "$1_rc"
}

# build UI's:
echo "building user interfaces..."
build_ui splash

# build resources
echo "building resources..."
build_res resources
