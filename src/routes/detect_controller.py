from flask import (
    Blueprint,
    request,
    Response,
    stream_with_context,
    json,
    jsonify,
    url_for,
)

from src.extensions import db
from src.models import HSBatch, HSImage, HSDefect
from src.detect_utils import detect, DEFECT_NAMES
from src.config import get_upload_folder

import os
from datetime import datetime

detect_bp = Blueprint("detect", __name__)


@detect_bp.route("/single-detect", methods=["POST"])
def single_detect():
    image_id = request.args.get("imageId")
    if not image_id:
        return {"error": "imageId is required"}, 400

    # 查询图片
    image = HSImage.query.filter_by(image_id=image_id).first()
    if not image:
        return {"error": "Image not found"}, 404

    # 读取图像文件字节并检测
    date_folder = image.create_time.strftime("%Y-%m-%d")
    file_path = os.path.join(
        get_upload_folder(), date_folder, image.image_original_path
    )
    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read image file: {e}"}), 500
    response = detect(image_bytes)
    has_defect = len(response.results) > 0
    # 保存处理后的图像
    time_now = datetime.now()
    processed_name = f"{os.path.splitext(image.image_original_path)[0]}_processed{os.path.splitext(image.image_original_path)[1]}"
    processed_folder = os.path.join(get_upload_folder(), date_folder)
    os.makedirs(processed_folder, exist_ok=True)
    processed_path = os.path.join(processed_folder, processed_name)
    with open(processed_path, "wb") as f:
        f.write(response.processed_image)
    image.image_processed_path = processed_name
    image.detect_time = time_now
    # 存储缺陷记录
    for det in response.results:
        defect = HSDefect(
            defect_type=DEFECT_NAMES[det.class_id],
            bbox=",".join(map(str, det.box)),
            confidence=det.confidence,
            image_id=image.image_id,
        )
        db.session.add(defect)
    db.session.commit()

    db.session.refresh(image)

    ret = {
        "hasDefect": has_defect,
        "imageId": image.image_id,
        "detectTime": image.detect_time,
        "processed": (
            None
            if image.image_processed_path is None
            else url_for(
                "static",
                filename=f"{image.detect_time.strftime('%Y-%m-%d')}/{image.image_processed_path}",
            )
        ),
        "defects": [
            {
                "defectId": defect.defect_id,
                "defectType": defect.defect_type,
                "bbox": defect.bbox,
                "confidence": defect.confidence,
            }
            for defect in image.defects
        ],
    }

    print(ret)
    return jsonify(ret), 200


@detect_bp.route("/batch-detect", methods=["POST"])
def batch_detect():
    batch_id = request.args.get("batchId")
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
        yield json.dumps(
            {"undetectedImageIds": [img.image_id for img in undetected_images]}
        )

        # 循环检测每张图片
        for image in undetected_images:
            # 读取图像文件并检测
            date_folder = image.create_time.strftime("%Y-%m-%d")
            file_path = os.path.join(
                get_upload_folder(), date_folder, image.image_original_path
            )
            try:
                with open(file_path, "rb") as f:
                    img_bytes = f.read()
            except Exception as e:
                yield json.dumps(
                    {"imageId": image.image_id, "error": f"Read error: {e}"}
                )
                continue
            response = detect(img_bytes)
            has_defect = len(response.results) > 0
            # 持久化结果
            time_now = datetime.now()
            processed_name = f"{os.path.splitext(image.image_original_path)[0]}_processed{os.path.splitext(image.image_original_path)[1]}"
            processed_folder = os.path.join(get_upload_folder(), date_folder)
            os.makedirs(processed_folder, exist_ok=True)
            processed_path = os.path.join(processed_folder, processed_name)
            with open(processed_path, "wb") as f:
                f.write(response.processed_image)
            image.image_processed_path = processed_name
            image.detect_time = time_now
            for det in response.results:
                defect = HSDefect(
                    defect_type=DEFECT_NAMES[det.class_id],
                    bbox=",".join(map(str, det.box)),
                    confidence=det.confidence,
                    image_id=image.image_id,
                )
                db.session.add(defect)
            db.session.commit()
            yield json.dumps({"imageId": image.image_id, "hasDefect": has_defect})

    return Response(
        stream_with_context(generate()), headers={"Content-Type": "application/json"}
    )
