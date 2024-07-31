from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
import cv2
import numpy as np
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
from ultralytics import YOLO
np.bool = np.bool_
async def main(service_config_path: Path, model_path: Path) -> None:
    # Load YOLO model
    model = YOLO(model_path)
    # model.to('cuda')  # Move model to GPU
    # model = model.export(format='engine', half=True, batch=1)
    # Create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.DRIVER_RECEIVE, "monotonic")
            or event.timestamps[0].stamp
        )
        
        # Cast image data bytes to numpy and decode
        image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
        
        # Run inference
        results = model(image,device=0)
        
        # Draw bounding boxes and labels
        for r in results:
            boxes = r.boxes
            for box in boxes:
                b = box.xyxy[0].tolist()  # get box coordinates in (top, left, bottom, right) format
                c = box.cls
                conf = box.conf.item()
                label = f"{model.names[int(c)]}: {conf:.2f}"
                cv2.rectangle(image, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (255, 0, 0), 2)
                cv2.putText(image, label, (int(b[0]), int(b[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
        
        # Visualize the image
        cv2.namedWindow("image", cv2.WINDOW_AUTOSIZE)
        cv2.imshow("image", image)
        cv2.waitKey(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream with strawberry detection.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--model-path", type=Path, required=True, help="Path to the YOLOv8 .pt model file.")
    args = parser.parse_args()
    asyncio.run(main(args.service_config, args.model_path))