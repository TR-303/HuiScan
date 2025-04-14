from flask import Blueprint, request, Response, stream_with_context, json
from src.models import HSBatch, HSImage
from src.detect_utils import detect

detect_bp = Blueprint('detect', __name__)


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
