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
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
np.bool = np.bool_

# TensorRT and CUDA setup
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
trt.init_libnvinfer_plugins(TRT_LOGGER, '')

def load_engine(engine_path):
    with open(engine_path, 'rb') as f, trt.Runtime(TRT_LOGGER) as runtime:
        engine = runtime.deserialize_cuda_engine(f.read())
    return engine

def allocate_buffers(engine):
    inputs = []
    outputs = []
    bindings = []
    for idx in range(engine.num_bindings):
        binding = engine[idx]
        shape = engine.get_binding_shape(binding)
        size = trt.volume(shape)
        dtype = trt.nptype(engine.get_binding_dtype(binding))
        host_mem = cuda.pagelocked_empty(size, dtype)
        device_mem = cuda.mem_alloc(host_mem.nbytes)
        bindings.append(int(device_mem))
        if engine.get_tensor_mode(binding) == trt.TensorIOMode.INPUT:
            inputs.append({'host': host_mem, 'device': device_mem})
        else:
            outputs.append({'host': host_mem, 'device': device_mem})
    return inputs, outputs, bindings

def preprocess_image(image):
    # Resize and normalize the image
    input_size = (640, 640)
    image = cv2.resize(image, input_size)
    image = image.astype(np.float32) / 255.0
    image = np.transpose(image, (2, 0, 1))  # HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    return image

def postprocess(outputs, image_size, input_size=(640, 640), conf_threshold=0.7):
    # Assuming outputs[0]['host'] contains the model output
    predictions = np.frombuffer(outputs[0]['host'], dtype=np.float32).reshape(1, -1, 6)  # Adjust 6 if different
    
    # Scale coordinates to original image size
    scale_x = image_size[1] / input_size[1]
    scale_y = image_size[0] / input_size[0]
    
    results = []
    for pred in predictions:
        boxes = []
        scores = []
        class_ids = []
        for detection in pred:
            confidence = detection[4] * detection[5]
            if confidence > conf_threshold:
                x1, y1, x2, y2 = detection[:4]
                x1 *= scale_x
                x2 *= scale_x
                y1 *= scale_y
                y2 *= scale_y
                boxes.append([x1, y1, x2, y2])
                scores.append(confidence)
                class_ids.append(0 if detection[5] > 0.5 else 1)  # Assuming binary classification
        
        results.append({
            'boxes': np.array(boxes),
            'scores': np.array(scores),
            'class_ids': np.array(class_ids)
        })
    
    return results

async def main(service_config_path: Path, engine_path: Path) -> None:
    # Load TensorRT engine
    engine = load_engine(engine_path)
    context = engine.create_execution_context()
    inputs, outputs, bindings = allocate_buffers(engine)

    input_shape = engine.get_binding_shape(0)  # Assuming the first binding is the input
    context.set_binding_shape(0, input_shape)

    # Create a client to the camera service
    config: EventServiceConfig = proto_from_json_file(service_config_path, EventServiceConfig())
    
    class_names = {0: 'Ripe', 1: 'Unripe'}  # Adjust based on your model's classes
    
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        stamp = (
            get_stamp_by_semantics_and_clock_type(event, StampSemantics.DRIVER_RECEIVE, "monotonic")
            or event.timestamps[0].stamp
        )
        
        # Cast image data bytes to numpy and decode
        image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
        
        # Preprocess the image
        input_data = preprocess_image(image)
        
        # Copy input data to the GPU
        np.copyto(inputs[0]['host'], input_data.ravel())
        cuda.memcpy_htod(inputs[0]['device'], inputs[0]['host'])
        
        # Run inference
        context.execute_v2(bindings=bindings)
        
        # Copy outputs from the GPU
        for out in outputs:
            cuda.memcpy_dtoh(out['host'], out['device'])
        
        # Postprocess the results
        results = postprocess(outputs, image.shape[:2])
        
        # Draw bounding boxes and labels
        for r in results:
            for box, score, class_id in zip(r['boxes'], r['scores'], r['class_ids']):
                x1, y1, x2, y2 = box
                class_name = class_names[class_id]
                label = f"{class_name}: {score:.2f}"
                cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                cv2.putText(image, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
        
        # Visualize the image
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        cv2.imshow("image", image)
        cv2.waitKey(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python main.py", description="Amiga camera-stream with strawberry detection.")
    parser.add_argument("--service-config", type=Path, required=True, help="The camera config.")
    parser.add_argument("--engine-path", type=Path, required=True, help="Path to the TensorRT engine file.")
    args = parser.parse_args()
    asyncio.run(main(args.service_config, args.engine_path))