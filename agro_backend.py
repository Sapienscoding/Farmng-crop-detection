from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Optional
import logging
import uvicorn

from farm_ng.core.event_client_manager import (
    EventClient,
    EventClientSubscriptionManager,
)
from farm_ng.core.event_service_pb2 import (EventServiceConfigList, SubscribeRequest, SubscribeReply)
from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.core.uri_pb2 import Uri
from fastapi import FastAPI,WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from inference import YoloInference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app with lifespan context manager
class AgroVisionApp(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = None
        self.inference = YoloInference()
        # self.inference_task = None
        self.inference_running = False
        self.current_oak = None
        
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )

    async def startup(self) -> None:
        print("Initializing App...")
        asyncio.create_task(event_manager.update_subscriptions())
        #start is a function to start the inference in yolo test.py

    def shutdown(self) -> None:
        print("Shutting down application: AgroVision")
    
    # async def start_inference(self):
    #     #run it on different thread using asyncio
    #     while True:
    #         if self.frame is not None:
    #             await self.inference.run_model(self.frame, args.model_path)
    #             await asyncio.sleep(0)
                

app = AgroVisionApp()
@app.on_event("startup")
async def startup_event():
    await app.startup()

@app.on_event("shutdown")
async def shutdown_event():
    app.shutdown()

# to store the events clients
clients: dict[str, EventClient] = {}

# @app.post('/oak/{oaknum}')
# # create grpc client
# async def SelectCamera(oaknum:int):
#     if oaknum not in [0,1]:
#         raise
#     client: EventClient = (
#         event_manager.clients['amiga']
#     )
#     print(f'receiving request for oak{oaknum}')
#     async for _, msg in client.subscribe(
#         SubscribeRequest(
#             uri=Uri(path=f"/rgb", query=f"service_name=oak/{oaknum}"),
#             every_n=2,
#         ),
#         decode=True,
#     ):
#         app.frame = msg.image_data

@app.websocket('/inference')
async def inference_websocket(websocket:WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            oaknum = int(data.replace('Oak', ''))
            if oaknum not in [0,1]:
                await websocket.send_text("Invalid camera selection")
            
            else:
                app.current_oak = oaknum
                app.inference_running = not app.inference_running
                status = 'started' if app.inference_running else 'stopped'
                # app.inference_task = asyncio.create_task(run_inference_loop(websocket, app.inference, args.model_path))
                await websocket.send_text(f"Inference {status} on camera Oak{oaknum}")
    except WebSocketDisconnect:
        logger.info("Inference WebSocket disconnected")
        app.inference_running = False
        app.current_oak = None

# @app.websocket("/subscribe/{service_name}/{uri_path:path}")
@app.websocket("/subscribe/{service_name}/{sub_service_name}/{uri_path:path}")
async def subscribe(
    websocket: WebSocket,
    service_name: str,
    uri_path: str,
    sub_service_name: Optional[str] = None,
    every_n: int = 2
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
    try:
        async for event, msg in client.subscribe(
            SubscribeRequest(
                uri=Uri(path=f"/{uri_path}", query=f"service_name={full_service_name}"),
                every_n=every_n,
            ),
            decode=True,
        ):
            # reply = SubscribeReply(event=event, payload=msg)
            # print("MSG PRINT", msg.image_data)
            app.frame = msg.image_data
            if app.inference_running and full_service_name == f'oak/{app.current_oak}':
                processed_frame = await app.inference.run_model(app.frame, args.model_path)
                await websocket.send_bytes(processed_frame)
            else:
                await websocket.send_bytes(app.frame)
    except WebSocketDisconnect:
        print(f'Websocket for {full_service_name} disconnected')
    finally:
        await websocket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True, help="config file")
    parser.add_argument("--port", type=int, default=8043, help="port to run the server")
    parser.add_argument("--model-path", type=Path, help=".engine file")
    parser.add_argument("--debug", action="store_true", help="debug mode")
    args = parser.parse_args()

    # NOTE: we only serve the react app in debug mode
    if not args.debug:
        react_build_directory = Path(__file__).parent / "agrovision" / "build"

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