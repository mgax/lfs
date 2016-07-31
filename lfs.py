import sys
import os
from pathlib import Path
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
import waitress
import flask
from werkzeug.wsgi import responder, FileWrapper
from werkzeug.wrappers import Request
from paste.cgiapp import CGIApplication

class LFS:

    def __init__(self, root):
        self.root = Path(root)
        self.tmp = self.root / 'tmp'
        self.objects = self.root / 'objects'

        self.root.mkdir(exist_ok=True)
        self.tmp.mkdir(exist_ok=True)
        self.objects.mkdir(exist_ok=True)

    @contextmanager
    def save(self, oid):
        d1 = self.objects / oid[:2]
        d2 = d1 / oid[2:4]
        obj = d2 / oid

        d1.mkdir(exist_ok=True)
        d2.mkdir(exist_ok=True)

        with NamedTemporaryFile(dir=str(self.tmp), delete=False) as tmp:
            yield tmp

        Path(tmp.name).rename(obj)

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
    lfs = LFS(app.config['PYLFS_ROOT'])

    @responder
    def dispatch(environ, start_response):
        request = Request(environ, shallow=True)

        if request.path in ['/info/refs', '/git-receive-pack']:
            environ['wsgi.errors'] = environ['wsgi.errors'].buffer.raw
            return git_app

        return flask_wsgi_app

    flask_wsgi_app = app.wsgi_app
    app.wsgi_app = dispatch

    @app.route('/.git/info/lfs/objects', methods=['POST'])
    def lfs_objects():
        oid = flask.request.json['oid']
        resp = flask.jsonify({
            '_links': {
                'upload': {
                    'href': app.config['SERVER_URL'] + '/upload/' + oid,
                },
            },
        })
        resp.status_code = 202
        return resp

    @app.route('/upload/<oid>', methods=['PUT'])
    def upload(oid):
        with lfs.save(oid) as f:
            for chunk in FileWrapper(flask.request.stream):
                f.write(chunk)

        return flask.jsonify(ok=True)

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
