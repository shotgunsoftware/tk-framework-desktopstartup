#!/usr/bin/env bash
#
# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# Stops the script
set -e

# Where we'll temporary create some files.
ROOT=/var/tmp/tmp_dir_`date +%y.%m.%d.%H.%M.%S`

abort()
{
    echo >&2 '
***************
*** ABORTED ***
***************
'
    echo "Cleaning up $ROOT..." >&2
    rm -rf $ROOT
    exit 1
}

trap 'abort' 0

# Git repo we'll clone
SRC_REPO=git@github.com:shotgunsoftware/tk-core.git
# Where we'll clone the repo
DEST_REPO=$ROOT/repo
# Destination relative to this script for the files
DEST=`pwd`/python/tk-core

# Recreate the folder structure
mkdir $ROOT
mkdir $DEST_REPO
# Strip files from the destination and recreate it.
rm -rf $DEST
mkdir -p $DEST
# Clone the repo
git clone $SRC_REPO $DEST_REPO --depth=1 -b $1

# Move to the git repo to generate the sha and write it to the $DEST
pushd $DEST_REPO
git rev-parse HEAD > $DEST/commit_id
popd

# Copy the files to the destination, but not the tests
cp -R $DEST_REPO/* $DEST
rm -rf $DEST/tests

# sed -i "" -e "s/version: \"HEAD\"/version: \"$1\"/" $DEST/info.yml

# Put files in the staging area.
git add -A $DEST
# Cleanup!
rm -rf $ROOT



trap : 0
