# Copyright (c) farm-ng, inc.
#
# Licensed under the Amiga Development Kit License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/farm-ng/amiga-dev-kit/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Optional

import uvicorn
from farm_ng.core.event_client_manager import (
    EventClient,
    EventClientSubscriptionManager,
)
from farm_ng.core.event_service_pb2 import EventServiceConfigList
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


# FastAPI app with lifespan context manager
class AgroVisionApp(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = None
        self.detected_frame = None


        self.inference = YoloInference()
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )

    def startup(self) -> None:
        print("Initializing App...")
        asyncio.create_task(event_manager.update_subscriptions())
        #start is a function to start the inference in yolo test.py
        self.start()

    def shutdown(self) -> None:
        print("Shutting down application: SettingApp")
    
    def start(self):
        #run it on different thread using asyncio
        while True:
            if self.frame is not None:
                self.inference.start(self.frame)
                

app = AgroVisionApp()
@app.on_event("startup")
async def startup_event():
    app.startup()

@app.on_event("shutdown")
async def shutdown_event():
    app.shutdown()

# to store the events clients
clients: dict[str, EventClient] = {}

@app.post('oak/{num}')
# create grpc client
async def SelectCamera(oak:int):
    client: EventClient = (
        event_manager.clients['amiga']
    )

    async for _, msg in client.subscribe(
        SubscribeRequest(
            uri=Uri(path=f"/rgb", query=f"service_name=oak/{oak}"),
            every_n=2,
        ),
        decode=True,
    ):
        app.frame = msg
@app.websocket("/subscribe/{service_name}/{uri_path:path}")
@app.websocket("/subscribe/{service_name}/{sub_service_name}/{uri_path:path}")
async def subscribe(
    websocket: WebSocket,
    service_name: str,
    uri_path: str,
    sub_service_name: Optional[str] = None,
    every_n: int = 1
):
    """Coroutine to subscribe to an event service via websocket.
    
    Args:
        websocket (WebSocket): the websocket connection
        service_name (str): the name of the event service
        uri_path (str): the uri path to subscribe to
        sub_service_name (str, optional): the sub service name, if any
        every_n (int, optional): the frequency to receive events. Defaults to 1.
    
    Usage:
        ws = new WebSocket("ws://localhost:8042/subscribe/gps/pvt")
        ws = new WebSocket("ws://localhost:8042/subscribe/oak/0/imu")
    """

    full_service_name = f"{service_name}/{sub_service_name}" if sub_service_name else service_name

    client: EventClient = (
        event_manager.clients[full_service_name]
        if full_service_name not in ["gps", "oak/0", "oak/1", "oak/2", "oak/3"]
        else event_manager.clients["amiga"]
    )
    

    await websocket.accept()

    async for _, msg in client.subscribe(
        SubscribeRequest(
            uri=Uri(path=f"/{uri_path}", query=f"service_name={full_service_name}"),
            every_n=every_n,
        ),
        decode=True,
    ):
        await websocket.send_json(MessageToJson(msg))

    await websocket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True, help="config file")
    parser.add_argument("--port", type=int, default=8042, help="port to run the server")
    parser.add_argument("--debug", action="store_true", help="debug mode")
    args = parser.parse_args()

    # NOTE: we only serve the react app in debug mode
    if not args.debug:
        react_build_directory = Path(__file__).parent / "ts" / "dist"

        app.mount(
            "/",
            StaticFiles(directory=str(react_build_directory.resolve()), html=True),
        )

    # config with all the configs
    base_config_list: EventServiceConfigList = proto_from_json_file(
        args.config, EventServiceConfigList()
    )

    # filter out services to pass to the events client manager
    service_config_list = EventServiceConfigList()
    for config in base_config_list.configs:
        if config.port == 0:
            continue
        service_config_list.configs.append(config)

    event_manager = EventClientSubscriptionManager(config_list=service_config_list)

    # run the server
    uvicorn.run(app, host="0.0.0.0", port=args.port)  # noqa: S104