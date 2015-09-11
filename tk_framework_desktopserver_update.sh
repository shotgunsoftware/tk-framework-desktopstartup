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
#    rm -rf $ROOT
exit 1
}

trap 'abort' 0

# Git repo we'll clone
SRC_REPO=git@github.com:shotgunsoftware/tk-framework-desktopserver.git
# Where we'll clone the repo
DEST_REPO=$ROOT/repo
# Zip file that will be generated from that repo
ZIP=$ROOT/tk-framework-desktopserver.zip
# Destination relative to this script for the files
DEST=`pwd`/python/server

# Recreate the folder structure
mkdir $ROOT
mkdir $DEST_REPO
# Strip files from the destination
rm -rf $DEST
# Clone the repo
git clone $SRC_REPO $DEST_REPO
# Generate the zip
git archive --format zip --output $ZIP --remote $DEST_REPO $1
# Unzip the files except for the tests.
unzip $ZIP -d $DEST -x tests/*
# Move to the git repo to generate the sha and write it to the $DEST
pushd $DEST_REPO
git rev-parse HEAD > $DEST/commit_id
popd
# Add the version in the info.yml
sed -i "" -e "s/version: \"HEAD\"/version: \"$1\"/" $DEST/info.yml
# Put files in the staging area.
git add -A $DEST
# Cleanup!
rm -rf $ROOT

trap : 0
