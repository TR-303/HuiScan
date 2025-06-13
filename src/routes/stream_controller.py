from flask_socketio import emit
from flask import request
import base64
from src.detect_utils import detect, DEFECT_NAMES
from src.extensions import db
from src.models import HSBatch, HSImage, HSDefect
from src.config import get_upload_folder
from datetime import datetime
import hashlib
import os
from src.rpc_client import DetectorClient
from PIL import Image

# track batch per client session
sessions = {}


def register_video_events(socketio):
    @socketio.on("frame", namespace="/video")
    def handle_video_frame(data):
        sid = request.sid  # 获取当前客户端的sid
        image_bytes = data
        try:
            # perform detection
            client = DetectorClient()
            response = client.detect(image_bytes)
            # print(f"Received detection response for session {sid}: {response}")
            # Build detection results list for overlay
            defects = []
            notifications_list = []
            for idx, result in enumerate(response.results):
                x1, y1, x2, y2 = result.box
                label = (
                    DEFECT_NAMES[result.class_id]
                    if result.class_id < len(DEFECT_NAMES)
                    else str(result.class_id)
                )
                defects.append(
                    {
                        "x": int(x1),
                        "y": int(y1),
                        "w": int(x2 - x1),
                        "h": int(y2 - y1),
                        "label": label,
                    }
                )
                notifications_list.append(
                    {"id": idx + 1, "type": label, "severity": "danger"}
                )
            emit(
                "processed_frame",
                {
                    "processed_image": response.processed_image,  # 直接 bytes
                    "defects": defects,
                    "notifications": notifications_list,
                },
                room=sid,
                namespace="/video",
            )
            # if defects found, save to batch/session
            if response.results:
                # create batch on first defect
                if sid not in sessions:
                    batch = HSBatch(import_time=datetime.now())
                    db.session.add(batch)
                    db.session.commit()
                    sessions[sid] = batch.batch_id
                batch_id = sessions[sid]
                # prepare storage folder
                date_folder = datetime.now().strftime("%Y-%m-%d")
                upload_dir = os.path.join(get_upload_folder(), date_folder)
                os.makedirs(upload_dir, exist_ok=True)
                # save raw image
                fname = (
                    hashlib.sha256(image_bytes).hexdigest()
                    + "_"
                    + datetime.now().strftime("%H%M%S%f")
                    + ".jpg"
                )
                raw_path = save_raw_image(image_bytes, upload_dir, fname)
                # save thumbnail
                thumb_name = (
                    os.path.splitext(fname)[0]
                    + "_thumbnail"
                    + os.path.splitext(fname)[1]
                )
                thumb_path = os.path.join(upload_dir, thumb_name)
                width, height = save_thumbnail(raw_path, thumb_path)
                # create image record
                img = create_image_record(fname, batch_id, width, height)
                # save processed image
                proc_name = (
                    os.path.splitext(fname)[0]
                    + "_processed"
                    + os.path.splitext(fname)[1]
                )
                save_processed_image(response.processed_image, upload_dir, proc_name)
                update_image_processed(img, proc_name)
                save_defects(img, response)
        except Exception as e:
            emit(
                "error",
                {"msg": f"Detection error: {str(e)}"},
                room=sid,
                namespace="/video",
            )


def save_raw_image(image_bytes, upload_dir, fname):
    raw_path = os.path.join(upload_dir, fname)
    with open(raw_path, "wb") as f:
        f.write(image_bytes)
    return raw_path


def save_thumbnail(raw_path, thumb_path):
    width, height = None, None
    try:
        img_pil = Image.open(raw_path)
        width, height = img_pil.size
        img_pil.thumbnail((150, 150))
        img_pil.save(thumb_path)
    except Exception:
        with open(raw_path, "rb") as src, open(thumb_path, "wb") as dst:
            dst.write(src.read())
    return width, height


def save_processed_image(processed_bytes, upload_dir, proc_name):
    proc_path = os.path.join(upload_dir, proc_name)
    with open(proc_path, "wb") as f:
        f.write(processed_bytes)
    return proc_path


def create_image_record(fname, batch_id, width, height):
    img = HSImage(
        image_original_path=fname,
        batch_id=batch_id,
        create_time=datetime.now(),
        width=width,
        height=height,
    )
    db.session.add(img)
    db.session.commit()
    return img


def update_image_processed(img, proc_name):
    img.image_processed_path = proc_name
    img.detect_time = datetime.now()
    db.session.add(img)
    db.session.commit()


def save_defects(img, response):
    for det in response.results:
        defect = HSDefect(
            defect_type=DEFECT_NAMES[det.class_id],
            bbox=",".join(map(str, det.box)),
            confidence=det.confidence,
            image_id=img.image_id,
        )
        db.session.add(defect)
    db.session.commit()
