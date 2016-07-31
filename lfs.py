import os
from pathlib import Path
import waitress
import flask
from werkzeug.wsgi import responder
from werkzeug.wrappers import Request
from paste.cgiapp import CGIApplication

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

def create_app():
    app = flask.Flask(__name__)
    app.config.from_pyfile('settings.py')
    git_app = create_git_app(app.config['GIT_PROJECT_ROOT'])

    @responder
    def dispatch(environ, start_response):
        request = Request(environ, shallow=True)

        if request.path in ['/info/refs', '/git-receive-pack']:
            environ['wsgi.errors'] = environ['wsgi.errors'].buffer.raw
            return git_app

        return flask_wsgi_app

    flask_wsgi_app = app.wsgi_app
    app.wsgi_app = dispatch
    return app

def main():
    port = int(os.environ.get('PORT') or 5000)
    app = create_app()

    def serve():
        waitress.serve(app.wsgi_app, host='localhost', port=port)

    if app.config.get('RELOADER'):
        from werkzeug._reloader import run_with_reloader
        run_with_reloader(serve)
    else:
        serve()

main()
