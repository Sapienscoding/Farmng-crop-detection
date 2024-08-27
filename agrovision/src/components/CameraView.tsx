import React, { useState, useEffect} from "react";

interface CameraViewProps {
  label: string;
  oakID: string;
  inferenceRunning: boolean;
  expanded: boolean;
  
}

const CameraView: React.FC<CameraViewProps> = ({ label, oakID, inferenceRunning, expanded }) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;

    

    const connectWebSocket = () => {
      const oakNumber = oakID.replace('Oak', '');
      const wsUrl = inferenceRunning ? `ws://${window.location.hostname}:8042/subscribe/oak/${oakNumber}` : `ws://${window.location.hostname}:8042/subscribe/oak/${oakNumber}/rgb`;
      
      ws = new WebSocket(wsUrl);

      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = event.data;
        const blob = new Blob([data], {type: "image/jpeg"})
        const image = URL.createObjectURL(blob);
        setImageUrl(image)
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [oakID, inferenceRunning]);
  return (
    <div className={`camera-label ${expanded ? 'expanded' : ' '}`}>
      {label}
      <div className="cameraview-component">
        {imageUrl ? (
        <img src={imageUrl} alt={`Camera ${oakID} view`} className="Stream"/>
        ) : (
        <p>connecting to camera...</p>
        )}
      </div>
    </div>
  );
};

export default CameraView;
