import React, { useState, useEffect, useRef } from "react";

// import { SubscribeReply, OakFrame } from "farm_ng_proto";
// import { error } from "console";

interface CameraViewProps {
  label: string;
  oakID: string;
  
}

const CameraView: React.FC<CameraViewProps> = ({ label, oakID }) => {
  // const [imageSrc, setImageSrc] = useState<string>("");
  const imageSrc = useRef<HTMLImageElement>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const url_1 = `ws://${window.location.host}:${window.location.port}/preview/${oakID}`;
    const ws = new WebSocket(url_1);

    ws.onopen = () => {
      console.log('Websocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (Event) => {
      if (imageSrc.current) {
        const blob = new Blob([Event.data], {type:'image/jpeg'});
        const url = URL.createObjectURL(blob);
        imageSrc.current.src = url;
      }
    };

    ws.onerror = (error) => {
      console.error('Webscocket error:', error);
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  },[oakID]);

  //   ws.binaryType = "arraybuffer";

  //   ws.onmessage = async (event: MessageEvent) => {
  //     const data = await event.data;

  //     const dataArray = new Uint8Array(data);

  //     const reply = SubscribeReply.fromBinary(dataArray);

  //     const frame = OakFrame.fromBinary(reply.paylaod);

  //     const blob = new Blob([frame.imageData], { type: "image/jpeg" });

  //     const imageUrl = URL.createObjectURL(blob);

  //     setImageSrc(imageUrl);
  //   };
  // }, [label]);

  return (
    <div className="camera-label">
      {label}
      <div className="cameraview-component">
      {/* <label htmlFor={label}>{label}</label>
      {imageSrc === "" ? <div></div> : <img src={imageSrc}></img>} */}
      {isConnected ? (
        <img ref={imageSrc} alt={'Oak' + {label}}/>
      ) : (
        <div>connecting to camera...</div>
      )}
      </div>
    </div>
  );
};

export default CameraView;
