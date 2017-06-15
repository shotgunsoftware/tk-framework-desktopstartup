wget https://github.com/shotgunsoftware/tk-desktop/archive/sso.zip
unzip sso.zip -d python/bundle_cache
rm -rf python/bundle_cache/tk-desktop
mv python/bundle_cache/tk-desktop-sso python/bundle_cache/tk-desktop
rm sso.zip

wget https://github.com/shotgunsoftware/tk-config-basic/archive/sso.zip
unzip sso.zip -d python/bundle_cache
rm -rf python/bundle_cache/tk-config-basic
mv python/bundle_cache/tk-config-basic-sso python/bundle_cache/tk-config-basic
rm sso.zip