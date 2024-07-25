from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
import cv2
import torch
import numpy as np
import cupy as cp
from farm_ng.core.event_client import EventClient
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.stamp import get_stamp_by_semantics_and_clock_type
from farm_ng.core.stamp import StampSemantics
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
np.bool = np.bool_
class TensorRTInference:
    def __init__(self, engine_path):
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(self.logger) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        self.inputs, self.outputs, self.bindings, self.stream = self.allocate_buffers()

    def allocate_buffers(self):
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()
        
        for idx in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(idx)
            shape = self.engine.get_tensor_shape(name)
            if shape[0] == -1:  # Dynamic batch size
                shape = (1,) + shape[1:]  # Assume batch size of 1 for now
            size = trt.volume(shape)
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            # Append the device buffer to device bindings.
            bindings.append(int(device_mem))
            
            # Append to the appropriate list.
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                inputs.append({"host": host_mem, "device": device_mem})
            else:
                outputs.append({"host": host_mem, "device": device_mem})
        
        return inputs, outputs, bindings, stream

    def infer(self, img):
        # Copy input image to pagelocked memory.
        np.copyto(self.inputs[0]["host"], img.ravel())
        
        # Transfer input data to the GPU.
        for inp in self.inputs:
            cuda.memcpy_htod_async(inp["device"], inp["host"], self.stream)
        
        # Run inference.
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # Transfer predictions back from the GPU.
        for out in self.outputs:
            cuda.memcpy_dtoh_async(out["host"], out["device"], self.stream)
        
        # CUDA operation: ensures that all previously enqueued CUDA operations in the given stream have completed before the host program continues execution
        self.stream.synchronize()
        
        # Return only the host outputs.
        return [out["host"] for out in self.outputs]

def process_output(output, img_shape, conf_threshold=0.9, iou_threshold=0.4):
    output = output.reshape((-1, 7))  # Reshape to [num_boxes, 7]
    valid = output[:, 4] > conf_threshold
    boxes = output[valid, :4]
    scores = output[valid, 4]
    classes = output[valid, 5].astype(int)
    
    if len(boxes) == 0:
        return np.array([]), np.array([]), np.array([])

    # Convert boxes from [x, y, w, h] to [x1, y1, x2, y2]
    boxes[:, 2:] += boxes[:, :2]
    
    # Scale boxes to original image size
    boxes[:, [0, 2]] *= img_shape[1] / 640
    boxes[:, [1, 3]] *= img_shape[0] / 640
    
    indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), conf_threshold, iou_threshold)

    if len(indices) == 0:
        return np.array([]), np.array([]), np.array([])
    
    return boxes[indices], scores[indices], classes[indices]

async def main(service_config_path: Path, engine_path: Path) -> None:
    if not torch.cuda.is_available():
        print("CUDA is not available")
    else:
        print(f"Using CUDA Device: {torch.cuda.get_device_name(0)}")

    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    trt_inference = TensorRTInference(engine_path)
    
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.DRIVER_RECEIVE, "monotonic")
            or event.timestamps[0].stamp
        )
        print(f"Timestamp: {stamp}\n")
        print(f"Meta: {message.meta}")
        print("###################\n")
        
        image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
        # if event.uri.path == "/disparity":
        #     image = cv2.applyColorMap(image * 3, cv2.COLORMAP_JET)
        
        # Preprocess image for inference
        input_image = cv2.resize(image, (640, 640))
        # OpenCV reads in BGR format
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        # Normalize image [0,1]
        input_image = input_image.astype(np.float32) / 255.0
        # Changes the order to (C,H,W)
        input_image = np.transpose(input_image, (2, 0, 1))
        input_image = np.expand_dims(input_image, axis=0)

        # Perform inference
        output = trt_inference.infer(input_image)[0]
        
        # Process output and draw bounding boxes
        boxes, scores, classes = process_output(output, image.shape)
        
        if len(boxes)>0:
            for box, score, cls in zip(boxes, scores, classes):
                x1, y1, x2, y2 = box.astype(int)
                label = f"{'Ripe' if cls == 0 else 'Unripe'}: {score:.2f}"
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, label, ((x1 + x2) // 2, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
        cv2.namedWindow("image", cv2.WINDOW_AUTOSIZE)
        cv2.imshow("image", image)
        cv2.waitKey(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream with strawberry detection.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--engine-path", type=Path, required=True, help="Path to the TensorRT engine file.")
    args = parser.parse_args()
    asyncio.run(main(args.service_config, args.engine_path))