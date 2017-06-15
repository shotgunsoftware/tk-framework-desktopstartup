To update the desktop startup to use the latest sso code
--------------------------------------------------------
- Update the sso branch from tk-core, tk-desktop and tk-framework-desktopstartup with the master branch
- Run ./sso_update.sh
- Commit everything and push to the sso branch. This releases the code to the public.

To update the launcher scripts in sso_launchers/<platform>
----------------------------------------------------------
- On Windows, run sso_update_launcher.bat
- On Linux or macOS, run sso_update_launchers.sh

To launch the Shotgun Desktop is SSO mode
-----------------------------------------
Use one of the launches from the sso_launchers/<platform> folders.