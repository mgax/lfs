import sys
import os
import re
from pathlib import Path
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
import waitress
import flask
from werkzeug.wsgi import responder, FileWrapper
from werkzeug.wrappers import Request
from paste.cgiapp import CGIApplication

def mkdir(p):
    try:
        p.mkdir()
    except FileExistsError:
        pass

class LFS:

    def __init__(self, root):
        self.root = root

    @contextmanager
    def save(self, oid):
        mkdir(self.root)

        tmpdir = self.root / 'tmp'
        mkdir(tmpdir)

        objects = self.root / 'objects'
        mkdir(objects)

        obj = self.path(oid)
        mkdir(obj.parent.parent)
        mkdir(obj.parent)

        with NamedTemporaryFile(dir=str(tmpdir), delete=False) as tmp:
            yield tmp

        Path(tmp.name).rename(obj)

    def path(self, oid):
        assert '/' not in oid
        return self.root / 'objects' / oid[:2] / oid[2:4] / oid

def create_git_app(repo):
    git_http_backend = Path(__file__).parent.absolute() / 'git-http-backend'
    cgi = CGIApplication({}, str(git_http_backend))

    @responder
    def git_app(environ, start_response):
        environ['GIT_PROJECT_ROOT'] = repo
        environ['GIT_HTTP_EXPORT_ALL'] = ''
        environ['REMOTE_USER'] = 'foo'
        return cgi

    return git_app

def create_app(config_file):
    app = flask.Flask(__name__)
    app.config.from_pyfile(config_file)
    git_app = create_git_app(app.config['GIT_PROJECT_ROOT'])

    def lfs(repo):
        return LFS(Path(app.config['GIT_PROJECT_ROOT']) / repo / 'lfs')

    @responder
    def dispatch(environ, start_response):
        request = Request(environ, shallow=True)

        git_backend_urls = [
            r'^/[^/]+/info/refs$',
            r'^/[^/]+/git-receive-pack$',
            r'^/[^/]+/git-upload-pack$',
        ]
        if any(re.match(p, request.path) for p in git_backend_urls):
            environ['wsgi.errors'] = environ['wsgi.errors'].buffer.raw
            return git_app

        return flask_wsgi_app

    flask_wsgi_app = app.wsgi_app
    app.wsgi_app = dispatch

    def data_url(repo, oid):
        return app.config['SERVER_URL'] + '/' + repo + '/lfs/' + oid

    @app.route('/<repo>/info/lfs/objects', methods=['POST'])
    def lfs_objects(repo):
        oid = flask.request.json['oid']
        resp = flask.jsonify({
            '_links': {
                'upload': {
                    'href': data_url(repo, oid),
                },
            },
        })
        resp.status_code = 202
        return resp

    @app.route('/<repo>/info/lfs/objects/batch', methods=['POST'])
    def batch(repo):
        flask.abort(404)

    @app.route('/<repo>/info/lfs/objects/<oid>')
    def lfs_get_oid(repo, oid):
        oid_path = lfs(repo).path(oid)
        if not oid_path.is_file():
            flask.abort(404)
        return flask.jsonify({
            'oid': oid,
            'size': oid_path.stat().st_size,
            '_links': {
                'download': {
                    'href': data_url(repo, oid),
                },
            },
        })

    @app.route('/<repo>/lfs/<oid>', methods=['PUT'])
    def upload(repo, oid):
        with lfs(repo).save(oid) as f:
            for chunk in FileWrapper(flask.request.stream):
                f.write(chunk)

        return flask.jsonify(ok=True)

    @app.route('/<repo>/lfs/<oid>')
    def download(repo, oid):
        oid_path = lfs(repo).path(oid)
        if not oid_path.is_file():
            flask.abort(404)
        return flask.helpers.send_file(str(oid_path))

    return app

def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'settings.py'

    port = int(os.environ.get('PORT') or 5000)
    app = create_app(config_file)

    def serve():
        waitress.serve(app.wsgi_app, host='localhost', port=port)

    if app.config.get('RELOADER'):
        from werkzeug._reloader import run_with_reloader
        run_with_reloader(serve)
    else:
        serve()

main()
