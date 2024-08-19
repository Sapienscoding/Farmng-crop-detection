from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Optional
import cv2
import uvicorn
import numpy as np
from farm_ng.core.event_client_manager import (
    EventClient,
    EventClientSubscriptionManager,
)
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.protobuf.json_format import MessageToJson
from inference import YoloInference

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/preview/{camera_id}")
async def preview_camera(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    
    config_path = f"path/to/service_config_{camera_id}.json"
    config: EventServiceConfig = proto_from_json_file(config_path, EventServiceConfig())
    
    async for event, message in EventClient(config).subscribe(config.subscriptions[0], decode=True):
        image = cv2.imdecode(np.frombuffer(message.image_data, dtype="uint8"), cv2.IMREAD_UNCHANGED)
        _, jpeg = cv2.imencode('.jpg', image)
        await websocket.send_bytes(jpeg.tobytes())

if __name__== '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--congif', type=Path, required=True, help='config file')
    args = parser.parse_args()