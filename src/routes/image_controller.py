from flask import Blueprint, request, jsonify, url_for

from src.models import HSImage

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
                                                                             filename=f"{image.create_time.strftime('%Y-%m-%d')}/{image.image_processed_path}"),
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
