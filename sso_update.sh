./tk_core_update.sh sso

rm sso.zip
rm master.zip

rm -rf python/bundle_cache

wget https://github.com/shotgunsoftware/tk-desktop/archive/sso.zip
unzip sso.zip -d python/bundle_cache
mv python/bundle_cache/tk-desktop-sso python/bundle_cache/tk-desktop
rm sso.zip

wget https://github.com/shotgunsoftware/tk-config-basic/archive/master.zip
unzip master.zip -d python/bundle_cache
mv python/bundle_cache/tk-config-basic-master python/bundle_cache/tk-config-basic
echo 'location: {type: path, path: $SGTK_DESKTOP_STARTUP_LOCATION/python/tk-core}' > python/bundle_cache/tk-config-basic/core/core_api.yml
rm master.zip

git add python/bundle_cache