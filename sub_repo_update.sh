# Updates all sub repos to the latest of each branch they are tracking
git submodule deinit -f .
git submodule init
git submodule update

