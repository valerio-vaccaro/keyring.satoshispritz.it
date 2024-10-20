from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

import subprocess


app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/key')
def key():
    uid = request.args.get('uid')
    file = subprocess.run(['cat', f'static/{uid}.txt'], stdout=subprocess.PIPE).stdout.decode('ascii')
    info = subprocess.run(['ots-cli.js', 'i', f'static/{uid}.txt.ots'], stdout=subprocess.PIPE).stdout.decode('ascii')
    verify = subprocess.run(['ots-cli.js', 'v', f'static/{uid}.txt.ots', '-i'], stdout=subprocess.PIPE).stdout.decode('ascii')
    data = {
        'uid': uid,
        'file': file,
        'info': info,
        'verify': verify,
    }
    return render_template('key.html', **data)
