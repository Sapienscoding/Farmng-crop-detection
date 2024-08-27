import React, { useState, useEffect } from 'react';
import DropdownSelect from './DropdownSelect';
import CameraView from './CameraView';
import ExitButton from './ExitButton';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faPlay} from '@fortawesome/free-solid-svg-icons';

const HomeScreen: React.FC = () => {
  const [selectedCrop, setSelectedCrop] = useState('Strawberry');
  const [selectedCamera, setSelectedCamera] = useState('Oak0');
  const [inferenceRunning, setInferenceRunning] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.hostname}:8042/inference`);
    
    socket.onopen = () => {
      console.log('WebSocket connected for inference');
      setWs(socket);
    };

    socket.onclose = () => {
      console.log('WebSocket closed for inference');
      setWs(null);
      setInferenceRunning(false);
    };

    return () => {
      socket.close();
    };
  }, []);

  const handleStartInference = () => {
    console.log('Starting inference');
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(selectedCamera);
      setInferenceRunning(true);
      console.log('Starting inference for', selectedCamera);
    } else {
      console.error('WebSocket is not connected');
    }
  };

  return (
    <div className='HomeScreen'>
      <h1>AgroVision</h1>
      <div className='drop-camera'>
        <div className='dropclubbed'>
          <DropdownSelect
            label="Select Crop"
            options={['Strawberry', 'Tomato']}
            value={selectedCrop}
            onChange={setSelectedCrop}
          />
          <DropdownSelect
            label="Select Camera"
            options={['Oak0', 'Oak1']}
            value={selectedCamera}
            onChange={setSelectedCamera}
          />
        </div>
        <CameraView
          label={selectedCamera + " View"}
          oakID={selectedCamera}
          inferenceRunning = {inferenceRunning}
          expanded={inferenceRunning}
        />
      </div>
      <div className='button-component'>
        <ExitButton/>
        <button className='start-inference' onClick={handleStartInference} disabled={inferenceRunning}>
          <FontAwesomeIcon icon={faPlay} size="xs"/>
          {inferenceRunning ? 'Inference Running' : 'Start Inference'}
        </button>
      </div>
    </div>
  );
};

export default HomeScreen;