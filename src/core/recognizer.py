import cv2
import numpy as np
from insightface.app import FaceAnalysis
from typing import Optional, List, Tuple


class FaceRecognizer:
    def __init__(self, model_name: str = 'buffalo_l', threshold: float = 0.4):
        self.threshold = threshold
        self.app = FaceAnalysis(name=model_name, providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
    
    def extract_feature(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """
        擷取人臉特徵
        
        Args:
            face_img: 人臉圖片 (BGR)
            
        Returns:
            512 維特徵向量，若失敗則回傳 None
        """
        faces = self.app.get(face_img)
        
        if len(faces) != 1:
            return None
        
        feature = faces[0].embedding
        # 正規化
        feature = feature / np.linalg.norm(feature)
        return feature.astype(np.float32)
    
    def compare(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """
        比較兩個特徵向量的相似度
        
        Args:
            feature1: 特徵向量 1
            feature2: 特徵向量 2
            
        Returns:
            餘弦相似度 (0~1)
        """
        similarity = np.dot(feature1, feature2)
        return float(similarity)
    
    def recognize(self, feature: np.ndarray, 
                 employee_features: List[Tuple[str, str, np.ndarray]]) -> Optional[Tuple[str, str, float]]:
        """
        辨識人臉
        
        Args:
            feature: 待辨識的特徵向量
            employee_features: 員工資料列表 [(employee_id, name, feature), ...]
            
        Returns:
            若成功辨識，回傳 (employee_id, name, confidence)，否則回傳 None
        """
        if not employee_features:
            return None
        
        best_match = None
        best_score = 0.0
        
        for emp_id, name, emp_feature in employee_features:
            score = self.compare(feature, emp_feature)
            if score > best_score:
                best_score = score
                best_match = (emp_id, name, score)
        
        if best_score >= self.threshold:
            return best_match
        
        return None
