import cv2
import numpy as np
from typing import Optional, Tuple
import os


class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.5):
        # 使用 OpenCV 的 Haar Cascade 進行人臉偵測
        # 尋找 OpenCV 的 haarcascade 檔案
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if not os.path.exists(cascade_path):
            raise FileNotFoundError(f"找不到 Haar Cascade 檔案: {cascade_path}")
        
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.min_confidence = min_detection_confidence
    
    def detect(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        偵測人臉
        
        Args:
            image: BGR 圖片
            
        Returns:
            若偵測到恰好一張人臉，回傳 (x, y, w, h)，否則回傳 None
        """
        # 轉換為灰階圖像以提升偵測速度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 偵測人臉
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # 只接受恰好偵測到一張人臉的情況
        if len(faces) != 1:
            return None
        
        x, y, w, h = faces[0]
        return (int(x), int(y), int(w), int(h))
    
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
