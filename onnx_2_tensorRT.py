import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np
import os
import argparse

def build_engine(onnx_file_path, engine_file_path, precision='fp16', max_workspace_size=1, input_shape=(1, 3, 640, 640)):
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    EXPLICIT_BATCH = 1 << (int)(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    
    with trt.Builder(TRT_LOGGER) as builder, \
         builder.create_network(EXPLICIT_BATCH) as network, \
         trt.OnnxParser(network, TRT_LOGGER) as parser:
        
        builder.max_batch_size = input_shape[0]
        config = builder.create_builder_config()
        config.max_workspace_size = max_workspace_size * (1 << 30)  # Convert to bytes
        
        if precision == 'fp16':
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)
            else:
                print("Warning: FP16 not supported on this platform. Using FP32 instead.")
        
        # Parse ONNX
        with open(onnx_file_path, 'rb') as model:
            if not parser.parse(model.read()):
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                raise ValueError("Failed to parse ONNX file")
        
        profile = builder.create_optimization_profile()
        profile.set_shape("images", input_shape, input_shape, input_shape)
        config.add_optimization_profile(profile)
        
        print("Building TensorRT engine. This may take a few minutes.")
        engine = builder.build_engine(network, config)
        if engine is None:
            raise RuntimeError("Failed to build TensorRT engine")
        
        print(f"Saving TensorRT engine to {engine_file_path}")
        with open(engine_file_path, 'wb') as f:
            f.write(engine.serialize())
        
        return engine

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert ONNX model to TensorRT engine")
    parser.add_argument('--onnx', type=str, required=True, help='Path to input ONNX file')
    parser.add_argument('--engine', type=str, required=True, help='Path to output TensorRT engine file')
    parser.add_argument('--precision', type=str, choices=['fp32', 'fp16'], default='fp16', help='Precision mode')
    parser.add_argument('--workspace', type=int, default=1, help='Max workspace size in GB')
    parser.add_argument('--input_shape', type=int, nargs=4, default=[1, 3, 640, 640], help='Input shape (N,C,H,W)')
    args = parser.parse_args()

    try:
        build_engine(args.onnx, args.engine, args.precision, args.workspace, tuple(args.input_shape))
        print(f"TensorRT engine has been successfully created and saved to {args.engine}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")