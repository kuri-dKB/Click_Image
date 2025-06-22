import os
import json
import shutil
from datetime import datetime
from uuid import uuid4
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CURRENT_DIR = os.path.join(DATA_DIR, 'current')
SNAPSHOT_DIR = os.path.join(DATA_DIR, 'snapshots')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')

os.makedirs(CURRENT_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def copy_folder(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def get_files(folder):
    files = []
    for root, _, filenames in os.walk(folder):
        for name in filenames:
            path = os.path.relpath(os.path.join(root, name), folder)
            files.append(path)
    return files


@app.route('/')
def index():
    history = load_history()
    history.sort(key=lambda x: x['timestamp'], reverse=True)
    return render_template('index.html', history=history)


@app.route('/snapshot', methods=['POST'])
def create_snapshot():
    message = request.form['message']
    snap_id = uuid4().hex[:7]
    dst = os.path.join(SNAPSHOT_DIR, snap_id)
    copy_folder(CURRENT_DIR, dst)
    files = get_files(dst)
    entry = {
        'id': snap_id,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'user': os.getenv('USER', 'unknown'),
        'message': message,
        'snapshot_path': dst,
        'files': files,
    }
    history = load_history()
    history.append(entry)
    save_history(history)
    return redirect(url_for('index'))


@app.route('/restore/<snap_id>', methods=['POST'])
def restore_snapshot(snap_id):
    src = os.path.join(SNAPSHOT_DIR, snap_id)
    if os.path.exists(src):
        copy_folder(src, CURRENT_DIR)
    return redirect(url_for('index'))


@app.route('/diff/<snap_id>')
def diff_snapshot(snap_id):
    import difflib
    src = os.path.join(SNAPSHOT_DIR, snap_id)
    diff_text = []
    for path in get_files(src):
        file_a = os.path.join(src, path)
        file_b = os.path.join(CURRENT_DIR, path)
        if not os.path.exists(file_b):
            with open(file_a, 'r', encoding='utf-8') as f:
                text_a = f.readlines()
            diff = difflib.unified_diff(text_a, [], fromfile=f'snapshot/{path}', tofile=f'current/{path}')
        else:
            with open(file_a, 'r', encoding='utf-8') as f:
                text_a = f.readlines()
            with open(file_b, 'r', encoding='utf-8') as f:
                text_b = f.readlines()
            diff = difflib.unified_diff(text_a, text_b, fromfile=f'snapshot/{path}', tofile=f'current/{path}')
        diff_text.extend(diff)
    diff_html = '<br>'.join(line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') for line in diff_text)
    return render_template('diff.html', diff=diff_html)


if __name__ == '__main__':
    app.run(debug=True)
