import sys
import os
import subprocess
import tempfile
import shutil
from time import time, sleep
from pathlib import Path
import pytest

hardwrk_jpg = Path(__file__).parent.absolute() / 'hardwrk.jpg'
oid = '0b4d4d1d01a07527855848f6764d2de7d7f0c0631d22eebe2eabbb1c1b8b10d9'

@pytest.fixture
def run(tmp):
    env = dict(
        os.environ,
        GIT_CONFIG_NOSYSTEM='on',
        HOME=str(tmp),
    )

    def run(cwd, *args):
        return subprocess.check_output(args, cwd=str(cwd), env=env)

    run(tmp, 'git', 'config', '--global', 'user.email', 'foo@example.fom')
    run(tmp, 'git', 'config', '--global', 'user.name', 'Foo')
    run(tmp, 'git', 'config', '--global', 'credential.helper', '')
    run(tmp, 'git', 'lfs', 'install')

    return run

def cp(a, b):
    shutil.copy(str(a), str(b))

@pytest.yield_fixture
def tmp():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

def wait_for_url(url):
    t0 = time()
    while True:
        try:
            subprocess.check_call(['curl', '-s', url])
            return
        except subprocess.CalledProcessError:
            if time() - t0 < 3:
                sleep(.1)
            else:
                raise

@pytest.yield_fixture
def server(tmp, run):
    port = '36356'
    app_url = 'http://localhost:' + port
    git_url = 'http://foo:bar@localhost:' + port + '/repo.git'

    run(tmp, 'git', 'init', '--bare', 'repo.git')

    repo = tmp / 'repo.git'
    with (tmp / 'settings.py').open('w') as settings_py:
        print("GIT_PROJECT_ROOT =", repr(str(tmp)), file=settings_py)
        print("SERVER_URL =", repr(app_url), file=settings_py)

    p = subprocess.Popen(
        ['python', 'lfs.py', str(tmp / 'settings.py')],
        env=dict(os.environ, PORT=port),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wait_for_url(git_url + '/info/refs')

    try:
        yield git_url

    finally:
        p.terminate()
        out, _ = p.communicate()
        assert not out, out.decode('utf-8')
        p.wait()

def test_push_and_clone(tmp, run, server):
    run(tmp, 'git', 'init', 'client')
    client = tmp / 'client'
    run(client, 'git', 'lfs', 'track', '*.jpg')
    cp(hardwrk_jpg, client / 'hardwrk.jpg')
    run(client, 'git', 'add', '-A')
    run(client, 'git', 'commit', '-m', 'the letter')
    run(client, 'git', 'remote', 'add', 'origin', server)
    run(client, 'git', 'push', 'origin', 'master')

    with hardwrk_jpg.open('rb') as f:
        orig = f.read()

    ob = tmp / 'repo.git' / 'lfs' / 'objects' / oid[:2] / oid[2:4] / oid
    with ob.open('rb') as saved:
        assert saved.read() == orig

    run(tmp, 'git', 'clone', server, 'theclone')

    with (tmp / 'theclone' / 'hardwrk.jpg').open('rb') as cloned:
        assert cloned.read() == orig
