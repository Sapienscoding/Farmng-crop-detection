import React, { useState, useEffect} from "react";

// import { SubscribeReply, OakFrame } from "farm_ng_proto";
// import { error } from "console";

interface CameraViewProps {
  label: string;
  oakID: string;
  
}

const CameraView: React.FC<CameraViewProps> = ({ label, oakID }) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;

    

    const connectWebSocket = () => {
      const oakNumber = oakID.replace('Oak', '');
      ws = new WebSocket(`ws://${window.location.hostname}:8042/subscribe/oak/${oakNumber}/rgb`);

      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = event.data;
        const blob = new Blob([data], {type: "image/jpeg"})
        const image = URL.createObjectURL(blob);
        setImageUrl(image)



        // if (data.image_data) {
        //   console.log("WS DATA", data)
        //   setImageUrl(`data:image/jpeg;base64,${data.image_data}`);
        // }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        // Attempt to reconnect after a delay
        
      };
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [oakID]);
  return (
    <div className="camera-label">
      {label}
      <div className="cameraview-component">
        {imageUrl ? (
        <img src={imageUrl} alt={`Camera ${oakID} view`} />
        ) : (
        <p>connecting to camera...</p>
        )}
      </div>
    </div>
  );
};

export default CameraView;
