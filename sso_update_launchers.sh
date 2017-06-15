
# Updates the Linux shell script.
echo "/opt/Shotgun/Python/bin/python - <<EOF" > sso_launchers/linux/launch_sso_beta.sh
cat launch_sso_beta.py >> sso_launchers/linux/launch_sso_beta.sh
chmod u+x sso_launchers/linux/launch_sso_beta.sh

# Udpates the Shotgun App for MacOS.
# Todo