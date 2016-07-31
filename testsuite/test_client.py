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

def run(cwd, *args):
    return subprocess.check_output(args, cwd=str(cwd))

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
def server(tmp):
    port = '36356'
    url = 'http://localhost:' + port

    run(tmp, 'git', 'init', '--bare', 'server.git')

    repo = tmp / 'server.git'
    with (tmp / 'settings.py').open('w') as settings_py:
        print("GIT_PROJECT_ROOT =", repr(str(repo)), file=settings_py)
        print("PYLFS_ROOT =", repr(str(repo / 'pylfs')), file=settings_py)
        print("SERVER_URL =", repr(url), file=settings_py)

    p = subprocess.Popen(
        ['python', 'lfs.py', str(tmp / 'settings.py')],
        env=dict(os.environ, PORT=port),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wait_for_url(url + '/info/refs')

    try:
        yield url + '/'

    finally:
        p.terminate()
        out, _ = p.communicate()
        assert not out, out.decode('utf-8')
        p.wait()

def test_push(tmp, server):
    run(tmp, 'git', 'init', 'client')
    client = tmp / 'client'
    run(client, 'git', 'lfs', 'track', '*.jpg')
    cp(hardwrk_jpg, client / 'hardwrk.jpg')
    run(client, 'git', 'add', '-A')
    run(client, 'git', 'commit', '-m', 'the letter')
    run(client, 'git', 'remote', 'add', 'origin', server)
    run(client, 'git', 'push', 'origin', 'master')

    ob = tmp / 'server.git' / 'pylfs' / 'objects' / oid[:2] / oid[2:4] / oid
    with hardwrk_jpg.open('rb') as orig, ob.open('rb') as saved:
        assert orig.read() == saved.read()
