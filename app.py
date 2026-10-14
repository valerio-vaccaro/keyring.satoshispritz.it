from flask import Flask, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import urlencode
from pathlib import Path
import re
import random
import subprocess

from translations import FILE_PAGE_TRANSLATIONS, LANGUAGES, NOT_FOUND_MESSAGES, TRANSLATIONS



app = Flask(__name__)


def current_language():
    requested = request.args.get('lang', 'it')
    supported = {code for code, _, _ in LANGUAGES}
    return requested if requested in supported else 'it'


@app.context_processor
def inject_language_helpers():
    def language_url(language):
        params = request.args.to_dict(flat=True)
        params['lang'] = language
        return f"{request.path}?{urlencode(params)}"

    language = current_language()
    return {
        'lang_url': language_url,
        'languages': LANGUAGES,
        't': {**TRANSLATIONS[language], **FILE_PAGE_TRANSLATIONS[language]},
    }

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route('/')
def hello():
    return render_template('index.html', lang=current_language())


def not_found_response():
    language = current_language()
    message = random.choice(NOT_FOUND_MESSAGES[language])
    return render_template(
        'not_found.html',
        lang=language,
        error_message=message,
    ), 404


@app.route('/key')
def key():
    uid = (request.args.get('uid') or '').strip().replace(':', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', uid):
        return not_found_response()

    static_dir = Path(app.root_path) / 'static'
    text_path = static_dir / f'{uid}.txt'
    pdf_path = static_dir / f'{uid}.pdf'
    if text_path.is_file():
        source_path = text_path
        is_pdf = False
    elif pdf_path.is_file():
        source_path = pdf_path
        is_pdf = True
    else:
        return not_found_response()

    filename = source_path.name
    proof_path = static_dir / f'{filename}.ots'
    file_content = '' if is_pdf else source_path.read_text(encoding='ascii', errors='replace')
    proof_unavailable = FILE_PAGE_TRANSLATIONS[current_language()]['proof_unavailable']
    if proof_path.is_file():
        try:
            info_result = subprocess.run(
                ['/usr/local/bin/ots-cli.js', 'i', str(proof_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors='replace',
                check=False,
            )
            verify_result = subprocess.run(
                ['/usr/local/bin/ots-cli.js', 'v', str(proof_path), '-i'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors='replace',
                check=False,
            )
            info = info_result.stdout.strip() or proof_unavailable
            verify = verify_result.stdout.strip() or proof_unavailable
        except OSError:
            info = proof_unavailable
            verify = proof_unavailable
    else:
        info = proof_unavailable
        verify = proof_unavailable

    data = {
        'uid': uid,
        'filename': filename,
        'file_url': url_for('static', filename=filename),
        'proof_filename': proof_path.name,
        'proof_url': url_for('static', filename=proof_path.name),
        'proof_exists': proof_path.is_file(),
        'file': file_content,
        'is_pdf': is_pdf,
        'info': info,
        'verify': verify,
        'lang': current_language(),
    }
    return render_template('key.html', **data)
