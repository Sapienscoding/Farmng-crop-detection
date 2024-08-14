import React from 'react';

interface CameraViewProps{
    label: string;
}

const CameraView: React.FC<CameraViewProps> = ({label}) => {
  return (
    <div className='camera-label'>{label} 
      <div className='cameraview-component'></div>
      {/* <label htmlFor={label}>{label}</label> */}
    </div>
  );
};

export default CameraView;