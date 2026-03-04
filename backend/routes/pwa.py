import os
from flask import Blueprint, send_from_directory

pwa_bp = Blueprint('pwa', __name__)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@pwa_bp.route('/service-worker.js')
def serve_service_worker():
    return send_from_directory(os.path.join(basedir, 'static'), 'service-worker.js',
                               mimetype='application/javascript')

@pwa_bp.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(basedir, 'static'), 'manifest.json',
                               mimetype='application/manifest+json')

@pwa_bp.route('/offline')
def offline_page():
    template_path = os.path.join(basedir, '../frontend/pages/offline/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@pwa_bp.route('/shared_assets/<path:filename>')
def serve_shared_assets(filename):
    shared_dir = os.path.join(basedir, '..', 'frontend', 'shared')
    return send_from_directory(shared_dir, filename)

@pwa_bp.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(os.path.join(basedir, 'uploads'), filename)
