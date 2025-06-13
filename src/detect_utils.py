import queue
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from src.rpc_client import DetectorClient

task_queue = queue.Queue()
results = {}
events = {}

DEFECT_NAMES = ["边缘裂纹", "横向裂纹", "表面杂质", "斑块缺陷"]
colors = [(255, 0, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255)]  # 蓝  # 绿  # 黄  # 红


def detection_worker(app):
    client = DetectorClient()
    with app.app_context():
        while True:
            task_id, image_bytes = task_queue.get()
            response = client.detect(image_bytes)
            results[task_id] = response
            events[task_id].set()
            task_queue.task_done()


def detect(image_bytes: bytes):
    """Accept raw image bytes, enqueue for detection, return DetectResponse"""
    task_id = f"task-{time.time_ns()}"
    events[task_id] = threading.Event()
    task_queue.put((task_id, image_bytes))
    events[task_id].wait()
    return results.pop(task_id)
