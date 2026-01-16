import sys
import os
import cv2
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, QTableWidget, 
                               QTableWidgetItem, QFileDialog, QMessageBox, 
                               QTabWidget, QGroupBox, QFormLayout)
from PySide6.QtCore import QTimer, Qt, Signal, QThread
from PySide6.QtGui import QImage, QPixmap
from PIL import Image, ImageDraw, ImageFont
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.detector import FaceDetector
from core.recognizer import FaceRecognizer
from core.database import Database
from core.liveness import LivenessDetector


class CameraThread(QThread):
    """攝影機執行緒"""
    frame_ready = Signal(np.ndarray)
    
    def __init__(self, camera_id: int = 0):
        super().__init__()
        self.camera_id = camera_id
        self.running = False
        self.cap = None
    
    def run(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
        
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            self.msleep(30)
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()


class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        
        # 初始化核心模組
        self.db = Database(config['database']['path'])
        self.detector = FaceDetector(config['face_detection']['min_detection_confidence'])
        self.recognizer = FaceRecognizer(
            model_name=config['face_recognition']['model'],
            threshold=config['face_recognition']['recognition_threshold']
        )
        self.liveness_detector = LivenessDetector()
        
        # 狀態變數
        self.current_frame = None
        self.camera_thread = None
        self.status_display_until = 0  # Timestamp to hold status message
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("人臉辨識打卡系統")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主 Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Tab Widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Tab 1: 員工註冊
        registration_tab = self.create_registration_tab()
        tabs.addTab(registration_tab, "員工註冊")
        
        # Tab 2: 打卡
        attendance_tab = self.create_attendance_tab()
        tabs.addTab(attendance_tab, "打卡")
        
        # Tab 3: 記錄查詢
        records_tab = self.create_records_tab()
        tabs.addTab(records_tab, "打卡記錄")
    
    def create_registration_tab(self) -> QWidget:
        """建立員工註冊頁面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 員工資訊輸入
        form_group = QGroupBox("員工資訊")
        form_layout = QFormLayout()
        
        self.reg_emp_id_input = QLineEdit()
        self.reg_name_input = QLineEdit()
        form_layout.addRow("員工 ID:", self.reg_emp_id_input)
        form_layout.addRow("姓名:", self.reg_name_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 照片選擇
        photo_group = QGroupBox("證件照")
        photo_layout = QVBoxLayout()
        
        self.reg_photo_label = QLabel("尚未選擇照片")
        self.reg_photo_label.setAlignment(Qt.AlignCenter)
        self.reg_photo_label.setMinimumHeight(300)
        self.reg_photo_label.setStyleSheet("border: 2px dashed #aaa;")
        photo_layout.addWidget(self.reg_photo_label)
        
        btn_layout = QHBoxLayout()
        self.btn_select_photo = QPushButton("選擇照片")
        self.btn_select_photo.clicked.connect(self.select_photo)
        self.btn_register = QPushButton("註冊員工")
        self.btn_register.clicked.connect(self.register_employee)
        self.btn_register.setEnabled(False)
        
        btn_layout.addWidget(self.btn_select_photo)
        btn_layout.addWidget(self.btn_register)
        photo_layout.addLayout(btn_layout)
        
        photo_group.setLayout(photo_layout)
        layout.addWidget(photo_group)
        
        # 員工列表
        list_group = QGroupBox("已註冊員工")
        list_layout = QVBoxLayout()
        
        self.reg_employee_table = QTableWidget()
        self.reg_employee_table.setColumnCount(3)
        self.reg_employee_table.setHorizontalHeaderLabels(["員工 ID", "姓名", "註冊時間"])
        list_layout.addWidget(self.reg_employee_table)
        
        self.btn_delete_employee = QPushButton("刪除選中員工")
        self.btn_delete_employee.clicked.connect(self.delete_employee)
        list_layout.addWidget(self.btn_delete_employee)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        self.update_employee_list()
        
        return widget
    
    def create_attendance_tab(self) -> QWidget:
        """建立打卡頁面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 攝影機畫面
        camera_group = QGroupBox("即時畫面")
        camera_layout = QVBoxLayout()
        
        self.camera_label = QLabel("攝影機未啟動")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumHeight(480)
        self.camera_label.setStyleSheet("border: 2px solid #333; background-color: #000;")
        camera_layout.addWidget(self.camera_label)
        
        # 狀態顯示
        self.status_label = QLabel("請啟動攝影機")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; padding: 10px;")
        camera_layout.addWidget(self.status_label)
        
        # 控制按鈕
        btn_layout = QHBoxLayout()
        self.btn_start_camera = QPushButton("啟動攝影機")
        self.btn_start_camera.clicked.connect(self.start_camera)
        self.btn_stop_camera = QPushButton("停止攝影機")
        self.btn_stop_camera.clicked.connect(self.stop_camera)
        self.btn_stop_camera.setEnabled(False)
        self.btn_checkin = QPushButton("立即打卡")
        self.btn_checkin.clicked.connect(self.check_in)
        self.btn_checkin.setEnabled(False)
        
        btn_layout.addWidget(self.btn_start_camera)
        btn_layout.addWidget(self.btn_stop_camera)
        btn_layout.addWidget(self.btn_checkin)
        camera_layout.addLayout(btn_layout)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        return widget
    
    def create_records_tab(self) -> QWidget:
        """建立記錄查詢頁面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 今日記錄
        today_group = QGroupBox("今日打卡記錄")
        today_layout = QVBoxLayout()
        
        self.today_table = QTableWidget()
        self.today_table.setColumnCount(5)
        self.today_table.setHorizontalHeaderLabels(["員工 ID", "姓名", "時間", "類型", "信心度"])
        today_layout.addWidget(self.today_table)
        
        self.btn_refresh = QPushButton("重新整理")
        self.btn_refresh.clicked.connect(self.update_today_records)
        today_layout.addWidget(self.btn_refresh)
        
        today_group.setLayout(today_layout)
        layout.addWidget(today_group)
        
        self.update_today_records()
        
        return widget
    
    def select_photo(self):
        """選擇證件照"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇證件照", "", "圖片檔案 (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            try:
                print(f"選擇的檔案路徑: {file_path}")
                
                # 讀取圖片（使用 imdecode 處理中文路徑）
                with open(file_path, 'rb') as f:
                    img_data = f.read()
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is None:
                    QMessageBox.warning(self, "錯誤", f"無法讀取圖片\n路徑: {file_path}")
                    print(f"無法讀取圖片: {file_path}")
                    return
                
                print(f"圖片尺寸: {img.shape}")
                
                # 偵測人臉
                bbox = self.detector.detect(img)
                print(f"人臉檢測結果: {bbox}")
                
                if bbox is None:
                    # 提供更詳細的錯誤信息
                    QMessageBox.warning(
                        self, "錯誤", 
                        "照片中必須恰好包含一張人臉\n\n提示：\n"
                        "• 確保照片中只有一個人\n"
                        "• 確保人臉清晰可見且正面朝向\n"
                        "• 確保照片光線充足"
                    )
                    print("未檢測到人臉或檢測到多張人臉")
                    return
                
                # 保存原始圖片（InsightFace 需要在原圖上檢測人臉）
                self.selected_photo = img
                
                # 裁切人臉用於顯示
                face_crop = self.detector.crop_face(img, bbox)
                print(f"裁切後的人臉尺寸: {face_crop.shape}")
                
                # 顯示裁切後的人臉
                self.display_image(face_crop, self.reg_photo_label)
                self.btn_register.setEnabled(True)
                print("照片選擇成功")
                
            except Exception as e:
                error_msg = f"處理照片時發生錯誤:\n{str(e)}"
                QMessageBox.critical(self, "錯誤", error_msg)
                print(f"錯誤: {error_msg}")
                import traceback
                traceback.print_exc()
    
    def register_employee(self):
        """註冊員工"""
        emp_id = self.reg_emp_id_input.text().strip()
        name = self.reg_name_input.text().strip()
        
        if not emp_id or not name:
            QMessageBox.warning(self, "錯誤", "請輸入員工 ID 和姓名")
            return
        
        if not hasattr(self, 'selected_photo'):
            QMessageBox.warning(self, "錯誤", "請先選擇證件照")
            return
        
        # 擷取特徵（使用原始圖片）
        print(f"正在提取特徵，圖片尺寸: {self.selected_photo.shape}")
        feature = self.recognizer.extract_feature(self.selected_photo)
        if feature is None:
            QMessageBox.warning(self, "錯誤", "無法擷取人臉特徵\n可能原因：\n• InsightFace 無法檢測到人臉\n• 人臉角度或光線不佳")
            print("特徵提取失敗")
            return
        
        print(f"特徵提取成功，特徵維度: {feature.shape}")
        
        # 儲存到資料庫
        success = self.db.add_employee(emp_id, name, feature)
        if success:
            QMessageBox.information(self, "成功", f"員工 {name} ({emp_id}) 註冊成功")
            self.reg_emp_id_input.clear()
            self.reg_name_input.clear()
            self.reg_photo_label.setText("尚未選擇照片")
            self.btn_register.setEnabled(False)
            delattr(self, 'selected_photo')
            self.update_employee_list()
        else:
            QMessageBox.warning(self, "錯誤", f"員工 ID {emp_id} 已存在")
    
    def delete_employee(self):
        """刪除員工"""
        selected_row = self.reg_employee_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請先選擇要刪除的員工")
            return
        
        emp_id = self.reg_employee_table.item(selected_row, 0).text()
        name = self.reg_employee_table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(
            self, "確認", f"確定要刪除員工 {name} ({emp_id}) 嗎？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.db.delete_employee(emp_id)
            if success:
                QMessageBox.information(self, "成功", "員工已刪除")
                self.update_employee_list()
            else:
                QMessageBox.warning(self, "錯誤", "刪除失敗")
    
    def update_employee_list(self):
        """更新員工列表"""
        employees = self.db.get_all_employees()
        self.reg_employee_table.setRowCount(len(employees))
        
        for i, (emp_id, name, _) in enumerate(employees):
            self.reg_employee_table.setItem(i, 0, QTableWidgetItem(emp_id))
            self.reg_employee_table.setItem(i, 1, QTableWidgetItem(name))
            # 這裡簡化處理，不顯示時間
            self.reg_employee_table.setItem(i, 2, QTableWidgetItem(""))
    
    def start_camera(self):
        """啟動攝影機"""
        self.camera_thread = CameraThread(self.config['camera']['device_id'])
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.start()
        
        self.btn_start_camera.setEnabled(False)
        self.btn_stop_camera.setEnabled(True)
        self.btn_checkin.setEnabled(False) # Wait for liveness
        self.status_label.setText("攝影機已啟動，請面向鏡頭並眨眼")
        self.liveness_detector.reset()
    
    def stop_camera(self):
        """停止攝影機"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait()
            self.camera_thread = None
        
        self.camera_label.setText("攝影機未啟動")
        self.btn_start_camera.setEnabled(True)
        self.btn_stop_camera.setEnabled(False)
        self.btn_checkin.setEnabled(False)
        self.status_label.setText("攝影機已停止")
    
    def update_camera_frame(self, frame: np.ndarray):
        """更新攝影機畫面"""
        self.current_frame = frame.copy()
        
        # 偵測人臉
        bbox = self.detector.detect(frame)
        
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Face Detected", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 活體偵測
            is_alive, msg = self.liveness_detector.process(frame)
            color = (0, 255, 0) if is_alive else (0, 0, 255)
            
            # Use PIL for Chinese text
            frame = self.draw_text_cn(frame, msg, (10, 30), color, 30)
            
            if is_alive:
                self.btn_checkin.setEnabled(True)
                if time.time() > self.status_display_until:
                    self.status_label.setText(f"✅ {msg}")
                    self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: green;")
            else:
                self.btn_checkin.setEnabled(False)
                if time.time() > self.status_display_until:
                    self.status_label.setText(f"👁️ {msg}")
                    self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: blue;")
        else:
            self.liveness_detector.reset()
            self.btn_checkin.setEnabled(False)
        
        # 顯示畫面
        self.display_image(frame, self.camera_label)
    
    def check_in(self):
        """執行打卡"""
        if self.current_frame is None:
            return
        
        # 偵測人臉
        bbox = self.detector.detect(self.current_frame)
        if bbox is None:
            self.status_label.setText("❌ 偵測失敗：畫面中必須恰好包含一張人臉")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: red;")
            return
        
        print(f"打卡 - 檢測到人臉: {bbox}")
        
        # 擷取特徵（使用原始畫面，讓 InsightFace 自己檢測）
        print(f"打卡 - 正在提取特徵，畫面尺寸: {self.current_frame.shape}")
        feature = self.recognizer.extract_feature(self.current_frame)
        if feature is None:
            self.status_label.setText("❌ 特徵擷取失敗")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: red;")
            print("打卡 - 特徵提取失敗")
            return
        
        print(f"打卡 - 特徵提取成功，特徵維度: {feature.shape}")
        
        # 取得所有員工特徵
        employees = self.db.get_all_employees()
        print(f"打卡 - 資料庫中有 {len(employees)} 位員工")
        
        # 辨識
        result = self.recognizer.recognize(feature, employees)
        
        if result is None:
            self.status_label.setText("❌ 辨識失敗：未找到匹配的員工")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: red;")
            self.status_display_until = time.time() + 3.0
            print("打卡 - 辨識失敗，未找到匹配的員工")
            return
        
        emp_id, name, confidence = result
        print(f"打卡 - 辨識成功: {name} ({emp_id})，信心度: {confidence:.3f}")
        
        # 檢查冷卻時間
        if self.db.check_recent_attendance(emp_id, self.config['attendance']['cooldown_minutes']):
            self.status_label.setText(f"⚠️ {name}，您在 {self.config['attendance']['cooldown_minutes']} 分鐘內已打卡")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: orange;")
            self.status_display_until = time.time() + 3.0
            print(f"打卡 - {name} 在冷卻時間內")
            return
        
        # 裁切人臉用於儲存照片
        face_img = self.detector.crop_face(self.current_frame, bbox)
        
        # 儲存打卡照片
        _, photo_bytes = cv2.imencode('.jpg', face_img)
        photo_blob = photo_bytes.tobytes()
        
        # 記錄打卡
        success = self.db.add_attendance_record(emp_id, name, confidence, photo_blob)
        
        if success:
            self.status_label.setText(f"✅ 打卡成功！{name} (信心度: {confidence:.2f})")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: green;")
            self.status_display_until = time.time() + 3.0  # Show success message for 3 seconds
            print(f"打卡 - 記錄成功")
            self.update_today_records()
            
            # Reset liveness after checkin
            self.liveness_detector.reset()
            self.btn_checkin.setEnabled(False)
        else:
            self.status_label.setText("❌ 記錄失敗")
            self.status_label.setStyleSheet("font-size: 16px; padding: 10px; color: red;")
            print("打卡 - 記錄失敗")
            self.status_display_until = time.time() + 3.0

    def draw_text_cn(self, img, text, pos, color=(0, 255, 0), size=20):
        """Draw Chinese text using PIL"""
        try:
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            # Try to load Windows font
            font = ImageFont.truetype("msjh.ttc", size, encoding="utf-8")
        except:
            try:
                font = ImageFont.truetype("arial.ttf", size, encoding="utf-8")
            except:
                font = ImageFont.load_default()
        
        draw.text(pos, text, font=font, fill=color)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    def update_today_records(self):
        """更新今日記錄"""
        records = self.db.get_today_attendance()
        self.today_table.setRowCount(len(records))
        
        for i, (emp_id, name, timestamp, rec_type, confidence) in enumerate(records):
            time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            self.today_table.setItem(i, 0, QTableWidgetItem(emp_id))
            self.today_table.setItem(i, 1, QTableWidgetItem(name))
            self.today_table.setItem(i, 2, QTableWidgetItem(time_str))
            self.today_table.setItem(i, 3, QTableWidgetItem(rec_type))
            self.today_table.setItem(i, 4, QTableWidgetItem(f"{confidence:.3f}"))
    
    def display_image(self, img: np.ndarray, label: QLabel):
        """顯示圖片到 QLabel"""
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        
        # 縮放以適應 label
        scaled_pixmap = pixmap.scaled(
            label.width(), label.height(), 
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        """關閉視窗時停止攝影機"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait()
        event.accept()
