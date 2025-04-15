import os.path
import queue
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from flask import current_app
from ultralytics import YOLO

from src.extensions import db
from src.models import HSImage, HSDefect
from src.config import get_upload_folder

MODEL_PATH = './models/seg_n.pt'
DEFECT_NAMES = ['边缘裂纹', '横向裂纹', '表面杂质', '斑块缺陷']
colors = [
    (255, 0, 0),  # 蓝
    (0, 255, 0),  # 绿
    (0, 255, 255),  # 黄
    (0, 0, 255)  # 红
]

task_queue = queue.Queue()
results = {}
events = {}
model = None


def init_yolo_model():
    global model
    if model is None:
        model = YOLO(MODEL_PATH,task='segment')


def detection_worker():
    while True:
        task_id, image_path = task_queue.get()
        result = model.predict(source=image_path, conf=0.4)
        results[task_id] = result
        events[task_id].set()
        task_queue.task_done()


init_yolo_model()
worker_thread = threading.Thread(target=detection_worker, daemon=True)
worker_thread.start()


def detect(image_id):
    with current_app.app_context():
        image = HSImage.query.get(image_id)
    image_path = os.path.join(get_upload_folder(), image.create_time.strftime('%Y-%m-%d'), image.image_original_path)
    task_id = f"task-{image_id}-{int(time.time() * 1000)}"
    events[task_id] = threading.Event()
    task_queue.put((task_id, image_path))
    events[task_id].wait()
    result = results.pop(task_id, None)

    if not result:
        return False

    r = result[0]  # 假设 result 只有一个元素
    boxes = r.boxes.xyxy  # 边界框的坐标 (x1, y1, x2, y2)
    scores = r.boxes.conf  # 置信度
    classes = r.boxes.cls  # 类别索引

    # 获取分割掩码
    masks = r.masks.data if r.masks else None

    img = cv2.imread(str(image_path))
    if masks is not None:
        for i,mask in enumerate(masks):
            class_id = int(classes[i].item())  # 转换为整数索引
            color = colors[class_id]

            # 处理mask数组
            mask_arr = (mask.cpu().numpy() * 255).astype(np.uint8)
            mask_arr = cv2.resize(mask_arr, (img.shape[1], img.shape[0]))

            # 创建彩色遮罩
            colored_mask = np.zeros_like(img, dtype=np.uint8)

            # 将颜色应用到三个通道（BGR顺序）
            colored_mask[:, :, 0] = color[0] * (mask_arr > 0)  # 蓝色通道
            colored_mask[:, :, 1] = color[1] * (mask_arr > 0)  # 绿色通道
            colored_mask[:, :, 2] = color[2] * (mask_arr > 0)  # 红色通道

            # 叠加到原图
            img = cv2.addWeighted(img, 1, colored_mask, 0.35, 0)

    time_now = datetime.now()

    processed_path = os.path.join(get_upload_folder(), time_now.strftime('%Y-%m-%d'),
                                  f"{image.image_original_path.split('.')[0]}_processed.{image.image_original_path.split('.')[1]}")
    cv2.imwrite(str(processed_path), img)
    image.image_processed_path = f"{image.image_original_path.split('.')[0]}_processed.{image.image_original_path.split('.')[1]}"

    with current_app.app_context():
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i].tolist()
            defect_type = DEFECT_NAMES[int(classes[i].item())]
            confidence = float(scores[i].item())
            defect = HSDefect(
                defect_type=defect_type,
                bbox=f"{x1},{y1},{x2},{y2}",
                confidence=confidence,
                image_id=image_id
            )
            db.session.add(defect)

        image.detect_time = time_now
        db.session.add(image)
        db.session.commit()

    return len(boxes) != 0
