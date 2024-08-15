from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
import cv2
import numpy as np
import time
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
from ultralytics import YOLO
np.bool = np.bool_


class YoloInference():
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        

    async def run_model(self,service_config_path: Path, model_path: Path) -> None:
        # Load YOLO model
        model = YOLO(model_path)
        
        # Create a client to the camera service
        config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())

        # run dummy inference to load up the model
        test_img = np.zeros((1080,1920,3),dtype=np.uint8)
        test_result = model(test_img, conf=0.6, half=True, device='CUDA')
        # print(model.names)
        t_end = time.monotonic()
        async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
            print("###########################")
            print(f"sleeptime:{int(1000*(time.monotonic()-t_end))}ms")
           
            # ds = message.meta.timestamp
            # dr = message.meta.timestamp_recv
            # ss = get_stamp_by_semantics_and_clock_type(event, StampSemantics.SERVICE_SEND, "monotonic")
            # cr = get_stamp_by_semantics_and_clock_type(event, StampSemantics.CLIENT_RECEIVE, "monotonic")
            # print(f'ds-dr = {int(1000*(dr-ds))}ms', f'dr-ss = {int(1000*(ss-dr))}ms', f'ss-cr = {int(1000*(cr-ss))}ms')
            # print(f'pipeline total = {int(1000*(cr-ds))}ms')
            t0 = time.monotonic()

            # Cast image data bytes to numpy and decode
            image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
            
            t1 = time.monotonic()
            # # Run inference
            results = model(image, conf=0.6, half=True, device='CUDA')

            t2 = time.monotonic()

            self.num_ripe = 0
            self.num_unripe = 0
            self.num_total = 0
            # Draw bounding boxes and labels
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    b = box.xyxy[0].tolist()  # get box coordinates in (top, left, bottom, right) format
                    c = box.cls
                    cls_name = model.names[int(c)]
                    conf = box.conf.item()
                    if (cls_name == 'ripe' and conf >= 0.6):
                        self.num_ripe += 1
                        color = (0,255,0) # bounding box for riped
                    else:
                        self.num_unripe += 1
                        color = (0,0,255) # bounding box for unriped
                    self.num_total = self.num_ripe + self.num_unripe
                    label = f"{cls_name}: {conf:.2f}"
                    detection_info = f'Ripe: {self.num_ripe}, Unripe: {self.num_unripe}, Total: {self.num_total}'
                    cv2.rectangle(image, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), color, 2)
                    cv2.putText(image, label, (int(b[0]), int(b[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
                    # Sow detection logs
                    cv2.putText(image, detection_info, (0,630), cv2.FONT_HERSHEY_SIMPLEX, 1, (128,0,0), 1, cv2.LINE_AA)
            
            # Visualize the image
            t3 = time.monotonic()
            cv2.namedWindow("image", cv2.WINDOW_AUTOSIZE)
            cv2.imshow("image", image)
            cv2.waitKey(1)
            t4 = time.monotonic()

            # Time took to run each part of the code and in total
            print(f'T1-T0 = {int(1000*(t1-t0))}ms', f'T2-T1 = {int(1000*(t2-t1))}ms', f'T3-T2 = {int(1000*(t3-t2))}ms', f'T4-T3 = {int(1000*(t4-t3))}ms')
            print(f'code total = {int(1000*(t4-t0))}ms')
            # print(f'total = {int(1000*(t4-ds))}ms')
            t_end = time.monotonic()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream with strawberry detection.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--model-path", type=Path, required=True, help="Path to the YOLOv8 .pt model file.")
    args = parser.parse_args()
    inference = YoloInference()
    asyncio.run(inference.run_model(args.service_config, args.model_path))

    # put time ticks in the for loop
    # How long the for loop sit
    # How old is to get the image
    # device sample -> device receive -> service send -> client receive
    # problem with oak service
    # Taking more time decoding and in inference    