./tk_core_update.sh sso

rm sso.zip

rm -rf python/bundle_cache

wget https://github.com/shotgunsoftware/tk-desktop/archive/sso.zip
unzip sso.zip -d python/bundle_cache
mv python/bundle_cache/tk-desktop-sso python/bundle_cache/tk-desktop
rm sso.zip

wget https://github.com/shotgunsoftware/tk-config-basic/archive/sso.zip
unzip sso.zip -d python/bundle_cache
mv python/bundle_cache/tk-config-basic-sso python/bundle_cache/tk-config-basic
rm sso.zip

git add python/bundle_cache