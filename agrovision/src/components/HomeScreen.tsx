import React, { useState, useEffect } from 'react';
import DropdownSelect from './DropdownSelect';
import CameraView from './CameraView';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlay, faBackward } from '@fortawesome/free-solid-svg-icons';

const HomeScreen: React.FC = () => {
  const [selectedCrop, setSelectedCrop] = useState('Strawberry');
  const [selectedCamera, setSelectedCamera] = useState('Oak0');

  const handleStartInference = () => {
    console.log('Starting inference');
    // Add your inference logic here
  };

  const handleExit = () => {
    console.log('Exiting app');
    // Add your exit logic here
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
        />
      </div>
      <div className='button-component'>
        <button className='exit' onClick={handleExit}>
          <FontAwesomeIcon icon={faBackward} size="xs"/>Exit to launcher</button>
        <button className='start-inference' onClick={handleStartInference}>
          <FontAwesomeIcon icon={faPlay} size="xs"/>Start Inference</button>
      </div>
    </div>
  );
};

export default HomeScreen;