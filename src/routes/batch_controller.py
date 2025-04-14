import hashlib
import os
from datetime import timedelta, datetime
from PIL import UnidentifiedImageError, Image
from dateutil.parser import parse
from flask import Blueprint, request, jsonify, url_for

from src.extensions import db
from src.config import get_upload_folder, get_allowed_extensions
from src.models import HSBatch, HSImage

batch_bp = Blueprint('batch', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()


@batch_bp.route('/create-batch', methods=['POST'])
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
            try:
                image = Image.open(file.stream)
            except (OSError, IOError, UnidentifiedImageError):
                continue
            width, height = image.size
            file_path = os.path.join(daily_folder, filename)
            image.save(file_path)

            # 存储缩略图
            thumbnail_path = os.path.join(daily_folder,
                                          os.path.splitext(filename)[0] + "_thumbnail" + os.path.splitext(filename)[1])
            try:
                image.thumbnail((150, 150))
                image.save(thumbnail_path)
            except (OSError, IOError):
                # 如果缩略图保存失败，用原图替代
                file.save(thumbnail_path)

            # 创建图片条目
            image_entry = HSImage(
                image_original_path=filename,
                batch_id=new_batch.batch_id,
                create_time=time_now,
                width=width,
                height=height
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


@batch_bp.route('/get-batch-list', methods=['GET'])
def get_batch_list():
    selectedDate = request.args.get('selectedDate')
    range_mode = request.args.get('rangeMode')
    sort_value = request.args.get('sortValue')
    finished_status = request.args.get('finishedStatus')
    query = HSBatch.query

    # 筛选时间
    if selectedDate != "undefined":
        try:
            selected_date = parse(selectedDate)
        except ValueError:
            return jsonify({'error': '日期格式错误'}), 400

        if range_mode == 'year':
            start_date = selected_date.replace(month=1, day=1)
            end_date = selected_date.replace(month=12, day=31, hour=23, minute=59, second=59)
        elif range_mode == 'month':
            start_date = selected_date.replace(day=1)
            next_month = (selected_date.month % 12) + 1
            end_date = selected_date.replace(month=next_month, day=1) - timedelta(seconds=1)
        elif range_mode == 'day':
            start_date = selected_date
            end_date = selected_date.replace(hour=23, minute=59, second=59)
        else:
            return jsonify({'error': '无效的 rangeMode 参数'}), 400

        query = query.filter(HSBatch.import_time >= start_date, HSBatch.import_time <= end_date)

    # 筛选完成状态
    if finished_status == 'finished':
        query = query.filter(~HSBatch.images.any(HSImage.detect_time.is_(None)))
    elif finished_status == 'unfinished':
        query = query.filter(HSBatch.images.any(HSImage.detect_time.is_(None)))

    # 根据 sort_value 排序
    if sort_value == 'time':
        query = query.order_by(HSBatch.import_time.asc())
    elif sort_value == '-time':
        query = query.order_by(HSBatch.import_time.desc())

    # 获取结果
    batches = query.all()
    result = [
        {
            'batchId': batch.batch_id,
            'importTime': batch.import_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': '已完成' if batch.get_batch_status() == 'finished' else '未完成',
            'size': batch.get_batch_size()
        }
        for batch in batches
    ]

    return jsonify(result), 200


@batch_bp.route('/get-batch-detail', methods=['GET'])
def get_batch_detail():
    batch_id = request.args.get('batchId')
    if not batch_id:
        return jsonify({'error': '缺少 batchId 参数'}), 400

    batch = HSBatch.query.get(batch_id)
    if not batch:
        return jsonify({'error': '未找到对应的批次'}), 404

    images = batch.images.all()
    result = {
        'batchId': batch.batch_id,
        'importTime': batch.import_time.strftime('%Y-%m-%d %H:%M:%S'),
        'size': batch.get_batch_size(),
        'status': '已完成' if batch.get_batch_status() == 'finished' else '未完成',
        'images': [
            {
                'imageId': image.image_id,
                'status': 'untouched' if image.detect_time is None else ('faulty' if image.defects.count() > 0 else 'flawless'),
                'thumbnail': url_for('static',
                                     filename=f"{image.create_time.strftime('%Y-%m-%d')}/{os.path.splitext(image.image_original_path)[0]}_thumbnail{os.path.splitext(image.image_original_path)[1]}")
            }
            for image in images
        ]
    }

    return jsonify(result), 200
