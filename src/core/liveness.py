import cv2
import numpy as np
import mediapipe as mp
import time
from typing import Tuple, Optional

class LivenessDetector:
    def __init__(self, ear_threshold: float = 0.25, blink_consecutive_frames: int = 2):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # EAR Thresholds
        self.ear_threshold = ear_threshold
        self.blink_consecutive_frames = blink_consecutive_frames
        
        # State
        self.blink_counter = 0
        self.is_alive = False
        self.last_alive_time = 0
        self.alive_timeout = 5.0  # Liveness status lasts for 5 seconds
        
        # Eye landmarks indices (MediaPipe FaceMesh)
        # Left eye: [33, 160, 158, 133, 153, 144]
        # Right eye: [362, 385, 387, 263, 373, 380]
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]

    def _calculate_ear(self, landmarks, indices, w, h) -> float:
        # Convert landmarks to pixel coordinates
        coords = []
        for idx in indices:
            lm = landmarks[idx]
            coords.append((int(lm.x * w), int(lm.y * h)))
            
        # Vertical distances
        v1 = np.linalg.norm(np.array(coords[1]) - np.array(coords[5]))
        v2 = np.linalg.norm(np.array(coords[2]) - np.array(coords[4]))
        
        # Horizontal distance
        h_dist = np.linalg.norm(np.array(coords[0]) - np.array(coords[3]))
        
        # EAR
        ear = (v1 + v2) / (2.0 * h_dist)
        return ear

    def process(self, image: np.ndarray) -> Tuple[bool, str]:
        """
        Process the image and return liveness status.
        
        Returns:
            (is_alive, message)
        """
        # Check if liveness is still valid
        if self.is_alive:
            if time.time() - self.last_alive_time < self.alive_timeout:
                return True, "活體驗證成功"
            else:
                self.is_alive = False
                self.blink_counter = 0

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        
        results = self.face_mesh.process(image_rgb)
        
        if not results.multi_face_landmarks:
            return False, "未偵測到人臉"
            
        face_landmarks = results.multi_face_landmarks[0].landmark
        
        left_ear = self._calculate_ear(face_landmarks, self.LEFT_EYE, w, h)
        right_ear = self._calculate_ear(face_landmarks, self.RIGHT_EYE, w, h)
        
        avg_ear = (left_ear + right_ear) / 2.0
        
        if avg_ear < self.ear_threshold:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.blink_consecutive_frames:
                self.is_alive = True
                self.last_alive_time = time.time()
                self.blink_counter = 0
                return True, "活體驗證成功"
            
            self.blink_counter = 0
            
        return False, "請眨眼以進行驗證"

    def reset(self):
        self.is_alive = False
        self.blink_counter = 0
        self.last_alive_time = 0
