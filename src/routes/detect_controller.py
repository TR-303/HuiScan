from flask import Blueprint, request, Response, stream_with_context, json, jsonify, url_for

from src.extensions import db
from src.models import HSBatch, HSImage
from src.detect_utils import detect

detect_bp = Blueprint('detect', __name__)


@detect_bp.route('/single-detect', methods=['POST'])
def single_detect():
    image_id = request.args.get('imageId')
    if not image_id:
        return {"error": "imageId is required"}, 400

    # 查询图片
    image = HSImage.query.filter_by(image_id=image_id).first()
    if not image:
        return {"error": "Image not found"}, 404

    # 检测图片
    has_defect = detect(image.image_id)

    db.session.refresh(image)

    ret = {
        'hasDefect': has_defect,
        'imageId': image.image_id,
        'detectTime': image.detect_time,
        'processed': None if image.image_processed_path is None else url_for('static',
                                                                             filename=f"{image.detect_time.strftime('%Y-%m-%d')}/{image.image_processed_path}"),
        'defects': [
            {
                'defectId': defect.defect_id,
                'defectType': defect.defect_type,
                'bbox': defect.bbox,
                'confidence': defect.confidence
            } for defect in image.defects
        ]
    }

    print(ret)
    return jsonify(ret), 200


@detect_bp.route('/batch-detect', methods=['POST'])
def batch_detect():
    batch_id = request.args.get('batchId')
    if not batch_id:
        return {"error": "batchId is required"}, 400

    # 查询批次
    batch = HSBatch.query.filter_by(batch_id=batch_id).first()
    if not batch:
        return {"error": "Batch not found"}, 404

    # 获取未检测的图片
    undetected_images = batch.images.filter(HSImage.detect_time.is_(None)).all()
    if not undetected_images:
        return {"message": "All images have been detected"}, 200

    def generate():
        # 第一次返回未检测图片的 ID 列表
        yield json.dumps({"undetectedImageIds": [img.image_id for img in undetected_images]})

        # 循环检测每张图片
        for image in undetected_images:
            has_defect = detect(image.image_id)

            yield json.dumps({"imageId": image.image_id, "hasDefect": has_defect})

    return Response(stream_with_context(generate()), headers={'Content-Type': 'application/json'})
