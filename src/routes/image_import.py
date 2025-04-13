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
        return jsonify({'error': '没有上传图片！'}), 400

    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': '没有上传图片！'}), 400

    # 创建一个新的批次
    new_batch = HSBatch(import_time=datetime.now())
    db.session.add(new_batch)
    db.session.flush()

    os.makedirs(get_upload_folder(), exist_ok=True)

    image_entries = []
    for file in files:
        if file and allowed_file(file.filename):
            time_now = datetime.now()
            date_folder = time_now.strftime('%Y-%m-%d')  # 按日创建目录
            daily_folder = os.path.join(get_upload_folder(), date_folder)
            os.makedirs(daily_folder, exist_ok=True)
            filename = hashlib.sha256(file.read()).hexdigest() + "_" + os.urandom(8).hex() + \
                       os.path.splitext(file.filename)[1]
            file.seek(0)
            file_path = os.path.join(daily_folder, filename)
            file.save(file_path)

            # 创建图片条目
            image_entry = HSImage(
                image_original_path=filename,
                batch_id=new_batch.batch_id,
                create_time=time_now,
            )
            image_entries.append(image_entry)

    if not image_entries:
        db.session.rollback()
        return jsonify({'error': '没有上传图片！'}), 400

    db.session.add_all(image_entries)
    db.session.commit()

    if len(image_entries) != len(files):
        return jsonify(
            {'message': f'部分图片上传失败：成功上传 {len(image_entries)} 张，共 {len(files)} 张',
             'batchId': new_batch.batch_id}), 206
    return jsonify({'message': '图片全部上传成功！', 'batchId': new_batch.batch_id}), 201
