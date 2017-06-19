export BRANCH_NAME=feature/sso

# Delete previous zip files of the master branch of tk-config-basic if it is still present.
echo Cleaning up bundle_cache and any possible leftovers from a previous run.
rm master.zip
# Wipe the current bundle cache
rm -rf python/bundle_cache

# Get the latest core update from the SSO branch.
echo Updating core to latest from feature/sso
./tk_core_update.sh $BRANCH_NAME

# The the latest tk-config-basic
echo Getting the latest tk-config-basic
wget https://github.com/shotgunsoftware/tk-config-basic/archive/master.zip
unzip master.zip -d python/bundle_cache

# Rename the folder so we can reliably refer to it regardless of which branch this could come from in the future.
mv python/bundle_cache/tk-config-basic-master python/bundle_cache/tk-config-basic

echo Updating tk-config-basic to use an SSO enabled core.
# Update the core_api.yml to use the same core in the config as the one that is bundled with the desktop startup,
# which is sso enabled.
echo 'location: {type: path, path: $SGTK_DESKTOP_STARTUP_LOCATION/python/tk-core}' > python/bundle_cache/tk-config-basic/core/core_api.yml
rm master.zip

echo Rewriting the sso sso_launchers

# Updates the Linux shell script.
echo "/opt/Shotgun/Python/bin/python - <<EOF" > sso_launchers/linux/launch_sso_beta.sh
cat sso_launchers/launch_sso_beta.py >> sso_launchers/linux/launch_sso_beta.sh
chmod u+x sso_launchers/linux/launch_sso_beta.sh 

# Big props to http://www.dostips.com/forum/viewtopic.php?f=3&t=5543&start=30. This is just awesmome.
echo '0<0# : ^' > sso_launchers/windows/launch_sso_beta.bat
echo '"""' >> sso_launchers/windows/launch_sso_beta.bat
echo '@echo off' >> sso_launchers/windows/launch_sso_beta.bat
echo '"C:\Program Files\Shotgun\Python"\python.exe "%~f0" %*' >> sso_launchers/windows/launch_sso_beta.bat
echo 'pause' >> sso_launchers/windows/launch_sso_beta.bat
echo 'goto :EOF' >> sso_launchers/windows/launch_sso_beta.bat
echo '"""' >> sso_launchers/windows/launch_sso_beta.bat
cat sso_launchers/launch_sso_beta.py >> sso_launchers/windows/launch_sso_beta.bat

# Udpates the Shotgun App for MacOS.
echo "/Applications/Shotgun.app/Resources/Python/bin/python - <<EOF" > sso_launchers/macOS/launch_sso_beta.sh
cat sso_launchers/launch_sso_beta.py >> sso_launchers/macOS/launch_sso_beta.sh
chmod u+x sso_launchers/macOS/launch_sso_beta.sh 

# get everything ready to be merged.
git add python/bundle_cache
git add sso_launchers
