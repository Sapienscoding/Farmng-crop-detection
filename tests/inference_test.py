import pytest
from unittest.mock import Mock, patch
import numpy as np
from pathlib import Path
import asyncio
import cv2
from inference import YoloInference

@pytest.fixture
def inference():
    return YoloInference()

@pytest.mark.asyncio
@patch('inference.YOLO')
@patch('inference.proto_from_json_file')
@patch('inference.EventClient')

async def test_run_model_initialization(mock_event_client, mock_proto, mock_yolo, inference):
    # Testing the initialization part of run_model 
    mock_config = Mock()
    mock_proto.return_value = mock_config
    mock_model = Mock()
    mock_yolo.return_value = mock_model

    await inference.run_model(Path('dummy_config.json'), Path('dummy_model.engine'))

    mock_yolo.assert_called_once_with(Path('dummy_model.engine'))
    mock_proto.assert_called_once_with(Path('dummy_config.json'), pytest.mock.ANY)
    # check if dummy inference run
    mock_model.assert_called_once()

    @patch('inference.cv2.imdecode')
    def test_img_decoding(mock_imdecode):
        # test image decoding
        dummy_img_data = b'dummy_img_data'
        mock_imdecode.return_value = np.zeros((100,100,3), dtype=np.uint8)
        img = cv2.imdecode(np.frombuffer(dummy_img_data, dtype='uint8'), cv2.IMREAD_UNCHANGED)
        mock_imdecode.asser_called_once()
        assert img.shape == (640,640,3)

    def test_detection_counting(inference):
        # Test the detection counting logic
        mock_result = Mock()
        mock_box1 = Mock(cls=0, conf=Mock(item=lambda: 0.7)) # ripe
        mock_box2 = Mock(cls=1, conf=Mock(item=lambda: 0.8)) # unripe
        mock_results.boxes = [mock_box1, mock_box2]
        