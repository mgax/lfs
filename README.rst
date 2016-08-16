PyLFS
=====

A minimal Python implementation of `git-lfs`_. Currently speaks the v1 legacy
api.

.. _git-lfs: https://github.com/github/git-lfs

.. image:: https://travis-ci.org/mgax/lfs.svg?branch=master
   :alt: Build Status
   :target: https://travis-ci.org/mgax/lfs

Setup
~~~~~
::

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

Using as remote
~~~~~~~~~~~~~~~
::

  git init repo
  cd repo
  git lfs track '*.jpg'
  curl -O https://rawgit.com/mgax/lfs/master/testsuite/hardwrk.jpg
  git add .
  git commit -m 'test data'
  git remote add origin http://foo:bar@localhost:5000/repo.git
  git push --set-upstream origin master
