import sys
import os
import yaml
from PySide6.QtWidgets import QApplication

# 將 src 目錄加入路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.main_window import MainWindow


def load_config(config_path: str) -> dict:
    """載入設定檔"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    # 載入設定
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    config = load_config(config_path)
    
    # 建立應用程式
    app = QApplication(sys.argv)
    app.setApplicationName("人臉辨識打卡系統")
    
    # 建立主視窗
    window = MainWindow(config)
    window.show()
    
    # 執行應用程式
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
