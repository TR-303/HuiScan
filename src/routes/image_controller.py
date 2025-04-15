from flask import Blueprint, request, jsonify, url_for

from src.models import HSImage, HSDefect

from flask import request, jsonify
from sqlalchemy import and_
from datetime import datetime
from collections import defaultdict


image_bp = Blueprint('image', __name__)


@image_bp.route('/get-image-detail', methods=['GET'])
def get_image_detail():
    image_id = request.args.get('imageId')
    if not image_id:
        return jsonify({'error': '缺少图片ID'}), 400

    image = HSImage.query.filter_by(image_id=image_id).first()
    if not image:
        return jsonify({'error': '图片未找到'}), 404

    image_detail = {
        'imageId': image.image_id,
        'original': None if image.image_original_path is None else url_for('static',
                                                                           filename=f"{image.create_time.strftime('%Y-%m-%d')}/{image.image_original_path}"),
        'processed': None if image.image_processed_path is None else url_for('static',
                                                                             filename=f"{image.detect_time.strftime('%Y-%m-%d')}/{image.image_processed_path}"),
        'createTime': image.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'detectTime': image.detect_time.strftime('%Y-%m-%d %H:%M:%S') if image.detect_time else None,
        'width': image.width,
        'height': image.height,
        'defects': [
            {
                'defectId': defect.defect_id,
                'defectType': defect.defect_type,
                'bbox': defect.bbox,
                'confidence': defect.confidence
            } for defect in image.defects
        ]
    }

    return jsonify(image_detail), 200


@image_bp.route('/get-image-list', methods=['GET'])
def get_images():
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    detected = request.args.get('detected')
    defect_type = request.args.get('defect_type')

    query = HSImage.query

    if start_time and end_time:
        query = query.filter(HSImage.create_time.between(start_time, end_time))

    if detected == 'true':
        query = query.filter(HSImage.detect_time.isnot(None))
    elif detected == 'false':
        query = query.filter(HSImage.detect_time.is_(None))

    results = []
    for img in query.all():
        defect_types = list({d.defect_type for d in img.defects})
        if defect_type and defect_type not in defect_types:
            continue
        results.append({
            'image_id': img.image_id,
            'create_time': img.create_time.strftime('%Y-%m-%d'),
            'detected': img.detect_time is not None,
            'detect_time': img.detect_time.strftime('%Y-%m-%d') if img.detect_time else None,
            'defect_types': defect_types or ['无缺陷']
        })

    return jsonify(results), 200

@image_bp.route('/get-image-statistics', methods=['GET'])
def get_statistics():
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    # print(f"start_time:{start_time}")
    # print(f"end_time:{end_time}")
    # for img in HSImage.query.all():
    #     print(img.create_time)
    start_date = datetime.strptime(start_time, "%Y-%m-%d") if start_time else None
    end_date = datetime.strptime(end_time, "%Y-%m-%d") if end_time else None
    if end_date:
        end_date = end_date.replace(hour=23, minute=59, second=59)

    images = HSImage.query.filter(HSImage.create_time.between(start_date, end_date)).all()

    # print(len(images))
    date_stats = defaultdict(lambda: {'total': 0, 'defect': 0, 'types': defaultdict(int)})
    defect_proportion = defaultdict(int)

    for img in images:
        date = img.create_time.strftime('%Y-%m-%d')
        date_stats[date]['total'] += 1
        if img.defects.count() > 0:
            date_stats[date]['defect'] += 1
            for d in img.defects:
                date_stats[date]['types'][d.defect_type] += 1
                defect_proportion[d.defect_type] += 1
        else:
            defect_proportion['无缺陷'] += 1

    dates = sorted(date_stats.keys())
    statisticsData = {
        'dates': dates,
        'total': [date_stats[d]['total'] for d in dates],
        'defect': [date_stats[d]['defect'] for d in dates]
    }

    singleStatisticsData = {
        'dates': dates
    }

    for defect_type in set(dt for d in dates for dt in date_stats[d]['types'].keys()):
        singleStatisticsData[defect_type] = [date_stats[d]['types'].get(defect_type, 0) for d in dates]

    proportionData = [{'name': k, 'value': v} for k, v in defect_proportion.items()]

    return jsonify({
        'statisticsData': statisticsData,
        'proportionData': proportionData,
        'singleStatisticsData': singleStatisticsData
    })