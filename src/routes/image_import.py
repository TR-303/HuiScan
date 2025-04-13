import hashlib
import os
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify

from src.models import HSBatch, HSImage
from src.extensions import db

import_bp = Blueprint('image', __name__)


def get_allowed_extensions():
    return current_app.config['ALLOWED_EXTENSIONS']


def get_upload_folder():
    return current_app.config['UPLOAD_FOLDER']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()


@import_bp.route('/create-batch', methods=['POST'])
def create_batch():
    if 'images' not in request.files:
        return jsonify({'error': 'No images part in the request'}), 400

    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': 'No images uploaded'}), 400

    # 创建一个新的批次
    new_batch = HSBatch(import_time=datetime.now())
    db.session.add(new_batch)
    db.session.flush()

    os.makedirs(get_upload_folder(), exist_ok=True)

    image_entries = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = hashlib.sha256(file.read()).hexdigest() + os.path.splitext(file.filename)[1]
            file.seek(0)
            file_path = os.path.join(get_upload_folder(), filename)
            file.save(file_path)

            # 创建图片条目
            image_entry = HSImage(
                image_original_path=file_path,
                batch_id=new_batch.batch_id,
                create_time=datetime.now()
            )
            image_entries.append(image_entry)

    if not image_entries:
        return jsonify({'error': 'No valid images uploaded'}), 400

    db.session.add_all(image_entries)
    db.session.commit()

    if len(image_entries) != len(files):
        return jsonify({'error': f'图片没有全部上传成功：{len(image_entries)}/{len(files)}'}), 206

    return jsonify({'message': '图片全部上传成功！', 'batch_id': new_batch.batch_id}), 201
