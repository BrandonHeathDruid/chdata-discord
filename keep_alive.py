from flask import Flask
from waitress import serve

app = Flask('')


@app.route('/ping')
def ping():
    return 'pong'


def run():
    serve(app, host='0.0.0.0', port=8080, url_scheme='https', ident=None)


if __name__ == '__main__':
    run()
