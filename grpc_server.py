import os
from concurrent import futures
import time
import grpc
import cv2
import numpy as np
from ultralytics import YOLO

import src.grpc.detect_pb2 as detect_pb2
import src.grpc.detect_pb2_grpc as detect_pb2_grpc

# Path to the YOLO model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "./models/seg_n.pt")
# Class names
DEFECT_NAMES = ["边缘裂纹", "横向裂纹", "表面杂质", "斑块缺陷"]
colors = [(255, 0, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255)]

# Load model globally
yolo_model = YOLO(MODEL_PATH, task="segment")


class DetectorServicer(detect_pb2_grpc.DetectorServicer):
    def Detect(self, request, context):
        # Decode raw image bytes
        nparr = np.frombuffer(request.image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Run prediction directly on image array
        result = yolo_model.predict(source=img, conf=0.4)
        r = result[0]
        response = detect_pb2.DetectResponse()
        # Apply masks and boxes
        if r.masks:
            masks = r.masks.data
            for i, mask in enumerate(masks):
                class_id = int(r.boxes.cls[i].item())
                mask_arr = (mask.cpu().numpy() * 255).astype(np.uint8)
                mask_arr = cv2.resize(mask_arr, (img.shape[1], img.shape[0]))
                colored_mask = np.zeros_like(img, dtype=np.uint8)
                colored_mask[:, :, 0] = colors[class_id][0] * (mask_arr > 0)
                colored_mask[:, :, 1] = colors[class_id][1] * (mask_arr > 0)
                colored_mask[:, :, 2] = colors[class_id][2] * (mask_arr > 0)
                img = cv2.addWeighted(img, 1, colored_mask, 0.35, 0)
        # Draw boxes
        for i, box in enumerate(r.boxes.xyxy):
            x1, y1, x2, y2 = box.tolist()
            response.results.add(
                box=[x1, y1, x2, y2],
                confidence=float(r.boxes.conf[i].item()),
                class_id=int(r.boxes.cls[i].item()),
            )
        # Encode processed image to bytes
        _, buffer = cv2.imencode(".jpg", img)
        response.processed_image = buffer.tobytes()
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    detect_pb2_grpc.add_DetectorServicer_to_server(DetectorServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
