import sys
import os
import cv2
import numpy as np
from datetime import datetime
import subprocess
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, QTableWidget, 
                               QTableWidgetItem, QFileDialog, QMessageBox, 
                               QTabWidget, QGroupBox, QFormLayout, QRadioButton,
                               QButtonGroup, QSpinBox, QDateEdit)
from PySide6.QtCore import QTimer, Qt, Signal, QThread, QDate
from PySide6.QtGui import QImage, QPixmap
from PIL import Image, ImageDraw, ImageFont
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.detector import FaceDetector
from core.recognizer import FaceRecognizer
from core.database import Database
from core.liveness import LivenessDetector


# --- Shared Helpers ---
def draw_text_cn(img, text, pos, color=(0, 255, 0), size=20):
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

def speak_text(text: str):
    """文字轉語音 (使用 Windows PowerShell)"""
    try:
        cmd = f'''Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'''
        subprocess.Popen(["powershell", "-Command", cmd], 
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"TTS Error: {e}")

def display_image(img: np.ndarray, label: QLabel):
    """顯示圖片到 QLabel"""
    if img is None:
        return
        
    # Convert BGR to RGB
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_img.shape
    bytes_per_line = ch * w
    
    qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(qt_img)
    
    # Resize keeping aspect ratio
    scaled_pixmap = pixmap.scaled(
        label.width(), label.height(),
        Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    
    label.setPixmap(scaled_pixmap)


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


# --- Widgets ---

class RegistrationWidget(QWidget):
    def __init__(self, db, detector, recognizer):
        super().__init__()
        self.db = db
        self.detector = detector
        self.recognizer = recognizer
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        form_group = QGroupBox("員工資訊")
        form_layout = QFormLayout()
        self.reg_emp_id_input = QLineEdit()
        self.reg_name_input = QLineEdit()
        form_layout.addRow("員工 ID:", self.reg_emp_id_input)
        form_layout.addRow("姓名:", self.reg_name_input)
        form_group.setLayout(form_layout)
        left_layout.addWidget(form_group)
        
        photo_group = QGroupBox("證件照")
        photo_layout = QVBoxLayout()
        self.reg_photo_label = QLabel("尚未選擇照片")
        self.reg_photo_label.setAlignment(Qt.AlignCenter)
        self.reg_photo_label.setMinimumHeight(200)
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
        left_layout.addWidget(photo_group)
        left_layout.addStretch()
        
        # Right Panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        list_group = QGroupBox("已註冊員工")
        list_layout = QVBoxLayout()
        self.reg_employee_table = QTableWidget()
        self.reg_employee_table.setColumnCount(3)
        self.reg_employee_table.setHorizontalHeaderLabels(["員工 ID", "姓名", "註冊時間"])
        self.reg_employee_table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.reg_employee_table)
        
        self.btn_delete_employee = QPushButton("刪除選中員工")
        self.btn_delete_employee.clicked.connect(self.delete_employee)
        list_layout.addWidget(self.btn_delete_employee)
        list_group.setLayout(list_layout)
        right_layout.addWidget(list_group)
        
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        self.update_employee_list()

    def select_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇證件照", "", "圖片檔案 (*.jpg *.jpeg *.png)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    img_data = f.read()
                img_array = np.frombuffer(img_data, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    raise Exception("無法讀取圖片")
                
                bbox = self.detector.detect(img)
                if bbox is None:
                    QMessageBox.warning(self, "錯誤", "照片中必須恰好包含一張人臉")
                    return
                
                self.selected_photo = img
                face_crop = self.detector.crop_face(img, bbox)
                display_image(face_crop, self.reg_photo_label)
                self.btn_register.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "錯誤", str(e))

    def register_employee(self):
        emp_id = self.reg_emp_id_input.text().strip()
        name = self.reg_name_input.text().strip()
        if not emp_id or not name:
            QMessageBox.warning(self, "錯誤", "請輸入員工 ID 和姓名")
            return
        if not hasattr(self, 'selected_photo'):
            return
            
        feature = self.recognizer.extract_feature(self.selected_photo)
        if feature is None:
            QMessageBox.warning(self, "錯誤", "特徵提取失敗")
            return
            
        if self.db.add_employee(emp_id, name, feature):
            QMessageBox.information(self, "成功", f"員工 {name} 註冊成功")
            self.reg_emp_id_input.clear()
            self.reg_name_input.clear()
            self.reg_photo_label.setText("尚未選擇照片")
            self.btn_register.setEnabled(False)
            delattr(self, 'selected_photo')
            self.update_employee_list()
        else:
            QMessageBox.warning(self, "錯誤", f"員工 ID {emp_id} 已存在")

    def delete_employee(self):
        selected_row = self.reg_employee_table.currentRow()
        if selected_row < 0:
            return
        emp_id = self.reg_employee_table.item(selected_row, 0).text()
        if QMessageBox.question(self, "確認", f"刪除 {emp_id}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if self.db.delete_employee(emp_id):
                self.update_employee_list()

    def update_employee_list(self):
        employees = self.db.get_all_employees()
        self.reg_employee_table.setRowCount(len(employees))
        for i, (emp_id, name, _) in enumerate(employees):
            self.reg_employee_table.setItem(i, 0, QTableWidgetItem(emp_id))
            self.reg_employee_table.setItem(i, 1, QTableWidgetItem(name))
            self.reg_employee_table.setItem(i, 2, QTableWidgetItem(""))


class AttendanceWidget(QWidget):
    attendance_recorded = Signal() # Signal when attendance is recorded
    
    def __init__(self, db, detector, recognizer, liveness, config):
        super().__init__()
        self.db = db
        self.detector = detector
        self.recognizer = recognizer
        self.liveness_detector = liveness
        self.config = config
        self.current_frame = None
        self.camera_thread = None
        self.status_display_until = 0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Type Selection
        type_group = QGroupBox("打卡類型")
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.rb_clock_in = QRadioButton("上班 (Clock In)")
        self.rb_clock_out = QRadioButton("下班 (Clock Out)")
        self.rb_break = QRadioButton("休息 (Break)")
        self.rb_clock_in.setObjectName("rb_in")
        self.rb_clock_out.setObjectName("rb_out")
        self.rb_break.setObjectName("rb_break")
        
        self.type_group.addButton(self.rb_clock_in, 1)
        self.type_group.addButton(self.rb_clock_out, 2)
        self.type_group.addButton(self.rb_break, 3)
        type_layout.addWidget(self.rb_clock_in)
        type_layout.addWidget(self.rb_clock_out)
        type_layout.addWidget(self.rb_break)
        
        self.break_duration_label = QLabel("時數:")
        self.break_duration_spin = QSpinBox()
        self.break_duration_spin.setRange(1, 8)
        self.break_duration_spin.setSuffix(" 小時")
        self.break_duration_spin.setValue(1)
        self.break_duration_label.hide()
        self.break_duration_spin.hide()
        type_layout.addWidget(self.break_duration_label)
        type_layout.addWidget(self.break_duration_spin)
        type_layout.addStretch()
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        self.type_group.buttonClicked.connect(self._on_type_changed)
        
        # Camera
        camera_group = QGroupBox("即時畫面")
        camera_layout = QVBoxLayout()
        self.camera_label = QLabel("攝影機未啟動")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumHeight(480)
        self.camera_label.setStyleSheet("border: 2px solid #333; background-color: #000;")
        camera_layout.addWidget(self.camera_label)
        
        self.status_label = QLabel("請啟動攝影機")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; padding: 10px;")
        camera_layout.addWidget(self.status_label)
        
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
        
        self.auto_select_attendance_type()

    def _on_type_changed(self, button):
        if button == self.rb_break:
            self.break_duration_label.show()
            self.break_duration_spin.show()
        else:
            self.break_duration_label.hide()
            self.break_duration_spin.hide()

    def auto_select_attendance_type(self):
        hour = datetime.now().hour
        if 7 <= hour < 12:
            self.rb_clock_in.setChecked(True)
            self._on_type_changed(self.rb_clock_in)
        elif hour >= 17:
            self.rb_clock_out.setChecked(True)
            self._on_type_changed(self.rb_clock_out)
        else:
            if not self.type_group.checkedButton():
                self.rb_clock_in.setChecked(True)

    def start_camera(self):
        self.camera_thread = CameraThread(self.config['camera']['device_id'])
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.start()
        self.btn_start_camera.setEnabled(False)
        self.btn_stop_camera.setEnabled(True)
        self.btn_checkin.setEnabled(False)
        self.status_label.setText("攝影機已啟動，請面向鏡頭並眨眼")
        self.liveness_detector.reset()

    def stop_camera(self):
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
        self.current_frame = frame.copy()
        bbox = self.detector.detect(frame)
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            is_alive, msg = self.liveness_detector.process(frame)
            color = (0, 255, 0) if is_alive else (0, 0, 255)
            frame = draw_text_cn(frame, msg, (10, 30), color, 30)
            
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
        
        display_image(frame, self.camera_label)

    def check_in(self):
        if self.current_frame is None: return
        bbox = self.detector.detect(self.current_frame)
        if bbox is None:
            self.status_label.setText("❌ 偵測失敗")
            speak_text("偵測失敗")
            return
        
        feature = self.recognizer.extract_feature(self.current_frame)
        if feature is None:
            self.status_label.setText("❌ 特徵擷取失敗")
            return
            
        employees = self.db.get_all_employees()
        result = self.recognizer.recognize(feature, employees)
        
        if result is None:
            self.status_label.setText("❌ 辨識失敗")
            self.status_display_until = time.time() + 3.0
            speak_text("辨識失敗")
            return
            
        emp_id, name, confidence = result
        
        record_type = "其他"
        duration = 0
        if self.rb_clock_in.isChecked(): record_type = "上班"
        elif self.rb_clock_out.isChecked(): record_type = "下班"
        elif self.rb_break.isChecked():
            record_type = "休息"
            duration = self.break_duration_spin.value()
            
        allow_checkin = True
        today_records = self.db.get_today_attendance()
        emp_records = [r for r in today_records if r[0] == emp_id]
        
        if emp_records:
            last_record = emp_records[0]
            last_type = last_record[3]
            last_time = datetime.fromisoformat(last_record[2])
            if last_type == record_type:
                diff_minutes = (datetime.now() - last_time).total_seconds() / 60
                if diff_minutes < self.config['attendance']['cooldown_minutes']:
                    self.status_label.setText(f"⚠️ {name} 重複打卡")
                    self.status_display_until = time.time() + 3.0
                    speak_text("重複打卡")
                    return

        face_img = self.detector.crop_face(self.current_frame, bbox)
        _, photo_bytes = cv2.imencode('.jpg', face_img)
        photo_blob = photo_bytes.tobytes()
        
        if self.db.add_attendance_record(emp_id, name, confidence, photo_blob, record_type, duration):
            msg = f"✅ {record_type}打卡成功！{name}"
            if record_type == "休息": msg += f" ({duration}小時)"
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: green;")
            self.status_display_until = time.time() + 3.0
            speak_text(f"{name} {record_type}打卡成功")
            
            try:
                original_feature = next((f for eid, _, f in employees if eid == emp_id), None)
                if original_feature is not None:
                    new_feature = self.recognizer.evolve_feature(original_feature, feature)
                    self.db.update_employee_feature(emp_id, new_feature)
            except: pass
            
            self.liveness_detector.reset()
            self.btn_checkin.setEnabled(False)
            self.attendance_recorded.emit()


class RecordsWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        date_group = QGroupBox("日期選擇")
        date_layout = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(QLabel("選擇日期:"))
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        summary_group = QGroupBox("每日工時統計")
        summary_layout = QVBoxLayout()
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels(["員工 ID", "姓名", "日期", "工時 (小時)"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        summary_layout.addWidget(self.summary_table)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        records_group = QGroupBox("詳細打卡記錄")
        records_layout = QVBoxLayout()
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(6)
        self.records_table.setHorizontalHeaderLabels(["員工 ID", "姓名", "時間", "類型", "信心度", "照片"])
        self.records_table.verticalHeader().setDefaultSectionSize(100)
        self.records_table.setColumnWidth(5, 120)
        records_layout.addWidget(self.records_table)
        records_group.setLayout(records_layout)
        layout.addWidget(records_group)
        
        self.btn_refresh = QPushButton("查詢 / 重新整理")
        self.btn_refresh.clicked.connect(self.update_records)
        layout.addWidget(self.btn_refresh)
        
        self.update_records()

    def update_records(self):
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        records = self.db.get_attendance_by_date_range(selected_date, selected_date)
        self.records_table.setRowCount(len(records))
        
        for i, (emp_id, name, timestamp, rec_type, confidence, photo_blob) in enumerate(records):
            time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            self.records_table.setItem(i, 0, QTableWidgetItem(emp_id))
            self.records_table.setItem(i, 1, QTableWidgetItem(name))
            self.records_table.setItem(i, 2, QTableWidgetItem(time_str))
            self.records_table.setItem(i, 3, QTableWidgetItem(rec_type))
            self.records_table.setItem(i, 4, QTableWidgetItem(f"{confidence:.3f}"))
            
            if photo_blob:
                try:
                    photo_array = np.frombuffer(photo_blob, dtype=np.uint8)
                    photo_img = cv2.imdecode(photo_array, cv2.IMREAD_COLOR)
                    display_image(photo_img, QLabel()) # Hack to create pixmap? No
                    # Inline display
                    if photo_img is not None:
                        rgb_img = cv2.cvtColor(photo_img, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_img.shape
                        qt_img = QImage(rgb_img.data, w, h, ch*w, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qt_img).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        img_label = QLabel()
                        img_label.setPixmap(pixmap)
                        img_label.setAlignment(Qt.AlignCenter)
                        self.records_table.setCellWidget(i, 5, img_label)
                except: pass
            else:
                self.records_table.setItem(i, 5, QTableWidgetItem("無照片"))
                
        hours_data = self.calculate_daily_hours(records)
        self.summary_table.setRowCount(len(hours_data))
        for i, (emp_id, name, hours) in enumerate(hours_data):
            self.summary_table.setItem(i, 0, QTableWidgetItem(emp_id))
            self.summary_table.setItem(i, 1, QTableWidgetItem(name))
            self.summary_table.setItem(i, 2, QTableWidgetItem(selected_date))
            self.summary_table.setItem(i, 3, QTableWidgetItem(f"{hours:.2f}"))

    def calculate_daily_hours(self, records):
        emp_records = {}
        for r in records:
            emp_id, name, timestamp, rec_type, _, _ = r
            if emp_id not in emp_records:
                emp_records[emp_id] = {'name': name, 'logs': []}
            emp_records[emp_id]['logs'].append({'time': datetime.fromisoformat(timestamp), 'type': rec_type})
        
        results = []
        for emp_id, data in emp_records.items():
            name = data['name']
            logs = sorted(data['logs'], key=lambda x: x['time'])
            total_seconds = 0
            start_time = None
            for log in logs:
                l_type = log['type']
                l_time = log['time']
                if l_type == '上班':
                    if start_time is None: start_time = l_time
                elif l_type in ['下班', '休息']:
                    if start_time is not None:
                        total_seconds += (l_time - start_time).total_seconds()
                        start_time = None
            results.append((emp_id, name, total_seconds / 3600.0))
        return results


# --- Windows ---

class BaseWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QWidget { background-color: #2b2b2b; color: #ffffff; font-family: "Microsoft JhengHei", "Segoe UI"; font-size: 14px; }
            QGroupBox { border: 2px solid #3d3d3d; border-radius: 8px; margin-top: 12px; font-weight: bold; color: #e0e0e0; padding: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #4da3ff; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #4da3ff; border-color: #4da3ff; color: #000; }
            QPushButton:pressed { background-color: #2b82df; }
            QPushButton:disabled { background-color: #333; color: #777; border-color: #444; }
            QLineEdit, QSpinBox { padding: 8px; border: 1px solid #555; border-radius: 4px; background-color: #363636; color: white; selection-background-color: #4da3ff; }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #4da3ff; }
            QTableWidget { background-color: #363636; gridline-color: #444; border: 1px solid #444; border-radius: 4px; }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section { background-color: #3d3d3d; padding: 6px; border: 1px solid #444; color: #e0e0e0; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #3d3d3d; border-radius: 8px; top: -1px; }
            QTabBar::tab { background: #363636; color: #aaa; padding: 10px 25px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; min-width: 80px; }
            QTabBar::tab:selected { background: #4da3ff; color: #fff; }
            QLabel { color: #fff; }

            /* Toggle Buttons for RadioButtons */
            QRadioButton { 
                background-color: #3d3d3d; 
                color: #e0e0e0; 
                padding: 12px 24px; 
                border-radius: 6px; 
                font-size: 16px; 
                font-weight: bold; 
                border: 2px solid #555; 
            }
            QRadioButton::indicator { width: 0px; height: 0px; }
            QRadioButton:checked { background-color: #4da3ff; border-color: #4da3ff; color: white; }
            
            /* Specific Colors for Clock In/Out */
            QRadioButton#rb_in:checked { background-color: #28a745; border-color: #28a745; }
            QRadioButton#rb_out:checked { background-color: #dc3545; border-color: #dc3545; }
            QRadioButton#rb_break:checked { background-color: #ffc107; border-color: #ffc107; color: black; }
        """)
        
        self.db = Database(config['database']['path'])
        self.init_models()

    def init_models(self):
        # Override if needed or load all
        pass

class RegistrationWindow(BaseWindow):
    def __init__(self, config):
        super().__init__(config)
        self.setWindowTitle("員工註冊系統")
        self.setGeometry(100, 100, 800, 600)
        
    def init_models(self):
        self.detector = FaceDetector(self.config['face_detection']['min_detection_confidence'])
        self.recognizer = FaceRecognizer(
            model_name=self.config['face_recognition']['model'],
            threshold=self.config['face_recognition']['recognition_threshold']
        )
        
        widget = RegistrationWidget(self.db, self.detector, self.recognizer)
        self.setCentralWidget(widget)

class AttendanceWindow(BaseWindow):
    def __init__(self, config):
        super().__init__(config)
        self.setWindowTitle("人臉辨識打卡系統")
        self.setGeometry(100, 100, 800, 700)
        
    def init_models(self):
        self.detector = FaceDetector(self.config['face_detection']['min_detection_confidence'])
        self.recognizer = FaceRecognizer(
            model_name=self.config['face_recognition']['model'],
            threshold=self.config['face_recognition']['recognition_threshold']
        )
        self.liveness = LivenessDetector()
        
        widget = AttendanceWidget(self.db, self.detector, self.recognizer, self.liveness, self.config)
        self.setCentralWidget(widget)
        
    def closeEvent(self, event):
        # Stop camera on close
        widget = self.centralWidget()
        if widget: widget.stop_camera()
        event.accept()

class RecordsWindow(BaseWindow):
    def __init__(self, config):
        super().__init__(config)
        self.setWindowTitle("打卡記錄查詢")
        self.setGeometry(100, 100, 1000, 600)
        
    def init_models(self):
        # No heavy models needed
        widget = RecordsWidget(self.db)
        self.setCentralWidget(widget)

class MainWindow(BaseWindow):
    """Unified Admin Window (Legacy/Admin)"""
    def __init__(self, config):
        super().__init__(config)
        self.setWindowTitle("人臉辨識打卡系統 (管理員模式)")
        self.setGeometry(100, 100, 1200, 800)
        
    def init_models(self):
        self.detector = FaceDetector(self.config['face_detection']['min_detection_confidence'])
        self.recognizer = FaceRecognizer(
            model_name=self.config['face_recognition']['model'],
            threshold=self.config['face_recognition']['recognition_threshold']
        )
        self.liveness = LivenessDetector()
        
        tabs = QTabWidget()
        
        self.reg_widget = RegistrationWidget(self.db, self.detector, self.recognizer)
        self.att_widget = AttendanceWidget(self.db, self.detector, self.recognizer, self.liveness, self.config)
        self.rec_widget = RecordsWidget(self.db)
        
        # Connect signals
        self.att_widget.attendance_recorded.connect(self.rec_widget.update_records)
        
        tabs.addTab(self.reg_widget, "員工註冊")
        tabs.addTab(self.att_widget, "打卡")
        tabs.addTab(self.rec_widget, "打卡記錄")
        
        tabs.setCurrentIndex(1)
        self.setCentralWidget(tabs)
        
    def closeEvent(self, event):
        self.att_widget.stop_camera()
        event.accept()

