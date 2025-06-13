import grpc
import detect_pb2
import detect_pb2_grpc


class DetectorClient:
    def __init__(self, target="localhost:50051"):
        # 要传图像，消息长度设置得大一点
        channel = grpc.insecure_channel(
            target,
            options=[
                ("grpc.max_send_message_length", 100 * 1024 * 1024),
                ("grpc.max_receive_message_length", 100 * 1024 * 1024),
            ],
        )
        self.stub = detect_pb2_grpc.DetectorStub(channel)

    def detect(self, image_bytes: bytes) -> detect_pb2.DetectResponse:
        request = detect_pb2.DetectRequest(image_data=image_bytes)
        return self.stub.Detect(request)
