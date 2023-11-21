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

echo "This script will update the local repository with the given version of the TK-CORE."
echo ""
echo "Script syntax: $0 tk-core-tag"
echo "For example:   $0 v0.20.17"
echo ""
echo ""
echo "A commit_id file will be written to the tk-core shotgun distribution to "
echo "indicate which version being bundled with core."
echo ""
echo "This script is intended to be used by developers and maintainers of the tk-core API."
echo ""
echo ""
echo ""

# Stops the script
set -e

# Where we'll temporary create some files.
ROOT="/var/tmp/tmp_dir_$(date +%y.%m.%d.%H.%M.%S)"

abort()
{
    echo >&2 '
***************
*** ABORTED ***
***************
'
    echo "Cleaning up $ROOT..." >&2
    rm -rf "$ROOT"
    exit 1
}

trap 'abort' 0

# Git repo we'll clone
SRC_REPO=git@github.com:shotgunsoftware/tk-core.git
# Where we'll clone the repo
DEST_REPO="$ROOT/repo"
# Destination relative to this script for the files
DEST="$(pwd)/python/tk-core"

# Recreate the folder structure
mkdir "$ROOT"
mkdir "$DEST_REPO"
# Strip files from the destination and recreate it.
rm -rf "$DEST"
mkdir -p "$DEST"

echo "Cloning TK-CORE into a temp location, hang on..."
# Clone the repo
git clone "$SRC_REPO" "$DEST_REPO" --depth=1 -b "$1"

echo "Copying TK-CORE to the required location..."

# Move to the git repo to generate the sha and write it to the $DEST
pushd "$DEST_REPO"
git rev-parse HEAD > "$DEST/commit_id"
popd

# Copy the files to the destination, but not the tests
cp -R "$DEST_REPO"/* "$DEST"
rm -rf "$DEST/tests"
rm -rf "$DEST/docs"

echo "Updating tk-core info.yml..."
sed -i "$DEST/info.yml" -e "s/version: \"HEAD\"/version: \"$1\"/"

cp python/tk-core/software_credits software_credits
git add software_credits

# Put files in the staging area.
echo "adding new files to git..."
git add -A "$DEST"
# Cleanup!
rm -rf "$ROOT"

echo ""
echo "All done! TK-CORE in $DEST has been updated to $1."
echo "The changes have been added to git and are ready to be committed."
trap : 0
