import sys
import os
import yaml
from PySide6.QtWidgets import QApplication

# 將 src 目錄加入路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ui.main_window import RegistrationWindow, AttendanceWindow, RecordsWindow, MainWindow

def load_config(config_path: str) -> dict:
    """載入設定檔"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_module.py [register|attendance|records|admin]")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    # 載入設定
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    config = load_config(config_path)
    
    app = QApplication(sys.argv)
    
    window = None
    if mode == 'register':
        app.setApplicationName("員工註冊系統")
        window = RegistrationWindow(config)
    elif mode == 'attendance':
        app.setApplicationName("人臉辨識打卡系統")
        window = AttendanceWindow(config)
    elif mode == 'records':
        app.setApplicationName("打卡記錄查詢")
        window = RecordsWindow(config)
    elif mode == 'admin':
        app.setApplicationName("人臉辨識打卡系統 (管理員)")
        window = MainWindow(config)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
        
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
