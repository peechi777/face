import cv2
import numpy as np
import mediapipe as mp
from typing import Optional, Tuple
import os


class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5):
        # 使用 MediaPipe 進行人臉偵測
        self.min_confidence = min_detection_confidence
        
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=self.min_confidence
        )
    
    def detect(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        偵測人臉
        
        Args:
            image: BGR 圖片
            
        Returns:
            若偵測到恰好一張人臉，回傳 (x, y, w, h)，否則回傳 None
        """
        # 轉換為 RGB 圖像 (MediaPipe 需要 RGB)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 偵測人臉
        results = self.face_detection.process(image_rgb)
        
        if not results.detections:
            return None
        
        # 只接受恰好偵測到一張人臉的情況
        if len(results.detections) != 1:
            return None
            
        detection = results.detections[0]
        bboxC = detection.location_data.relative_bounding_box
        
        h_img, w_img = image.shape[:2]
        x = int(bboxC.xmin * w_img)
        y = int(bboxC.ymin * h_img)
        w = int(bboxC.width * w_img)
        h = int(bboxC.height * h_img)
        
        return (x, y, w, h)
    
    def crop_face(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                  expand_ratio: float = 0.2) -> np.ndarray:
        """
        裁切人臉區域
        
        Args:
            image: 原始圖片
            bbox: (x, y, w, h)
            expand_ratio: 擴展比例
            
        Returns:
            裁切後的人臉圖片
        """
        x, y, w, h = bbox
        h_img, w_img = image.shape[:2]
        
        # 擴展邊界
        expand_w = int(w * expand_ratio)
        expand_h = int(h * expand_ratio)
        
        x1 = max(0, x - expand_w)
        y1 = max(0, y - expand_h)
        x2 = min(w_img, x + w + expand_w)
        y2 = min(h_img, y + h + expand_h)
        
        face_img = image[y1:y2, x1:x2]
        return face_img
