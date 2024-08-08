import React, {useState, useRef, useEffect, SetStateAction} from 'react';
import {useNavigate, NavigateOptions} from 'react-router-dom';

type HomeScreenProps = {
    setCurrentView: React.Dispatch<SetStateAction<"home" | "counter">>
}


const HomeScreen: React.FC<HomeScreenProps> = ({setCurrentView}) => {
    const [selectedCrop,  setSelectedCrop] = useState<string>('');
    const [selectedCamera, setSelectedCamera] = useState<string>('');
    const [stream, setStream] = useState<MediaStream | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);

    // let navigate = useNavigate();

    const crops = ['Strawberry','Tomato'];
    const cameras = ['Oak0', 'Oak1'];

    useEffect(() => {
        if (selectedCamera && videoRef.current) {
            navigator.mediaDevices.getUserMedia({video: true})
            .then(stream => {
                setStream(stream);
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            })
            .catch(err => console.error("Error accessing camera:", err));
        }
        return () => {
            if(stream){
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [selectedCamera]);

    const StartInference = () => {
        if (selectedCrop && selectedCamera) {
            //navigate('/inference', {state: {crop: selectedCrop, camera: selectedCamera}});
            setCurrentView("counter");
        } else {
            alert('Please select the the crop and camera before starting!');
        }
    };

    return(
        <div className='home-screen'>
            <h1>AgroVision</h1>

            <div className='dropdown-container'>
    
                <select
                    value={selectedCrop}
                    onChange={(e) => setSelectedCrop(e.target.value)}
                >
                    <option value="">Select Crop</option>
                    {crops.map(crop => (
                        <option key={crop} value={crop}>{crop}</option>
                    ))}
                </select>

                <select
                    value={selectedCamera}
                    onChange={(e) => setSelectedCamera(e.target.value)}
                >
                    <option value="">Select Camera</option>
                    {cameras.map(cameras => (
                        <option key={cameras} value={cameras}>{cameras}</option>
                    ))}
                </select>
            </div>

            {selectedCamera && (
                <div className={`camera-view ${selectedCamera.toLowerCase().replace(/\s+/g, '-')}`}>
                <h2> {selectedCamera} View</h2>
                <video ref={videoRef} autoPlay playsInline />
                </div>
            )}

            <button 
                onClick={StartInference}
                disabled={!selectedCrop || !selectedCamera}
            >
                Start Inference
                </button>
        </div>
    );
};

export default HomeScreen;