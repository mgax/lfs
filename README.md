# PyLFS

A minimal Python implementation of
[git-lfs](https://github.com/github/git-lfs). Currently speaks the v1 legacy
api.

[![Build Status](https://travis-ci.org/mgax/lfs.svg?branch=master)](https://travis-ci.org/mgax/lfs)

### Setup
```shell
virtualenv venv -p python3
source venv/bin/activate

mkdir data
git init --bare data/repo.git

git clone https://github.com/mgax/lfs.git

cat > lfs/settings.py <<EOF
GIT_PROJECT_ROOT = '`pwd`/data'
SERVER_URL = 'http://localhost:5000'
EOF

cd lfs
pip install -r requirements.txt
python lfs.py
```

### Using as remote
```shell
git init repo
cd repo
git lfs track '*.jpg'
curl -O https://rawgit.com/mgax/lfs/master/testsuite/hardwrk.jpg
git add .
git commit -m 'test data'
git remote add origin http://foo:bar@localhost:5000/repo.git
git push --set-upstream origin master
```
