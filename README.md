# 人臉辨識打卡系統

## 安裝步驟

1. 安裝 Python 3.10+
2. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 執行方式

```bash
cd d:\face
python src\main.py
```

## 使用說明

### 1. 員工註冊
- 切換到「員工註冊」頁籤
- 輸入員工 ID 和姓名
- 點選「選擇照片」上傳證件照（必須恰好包含一張人臉）
- 點選「註冊員工」完成註冊

### 2. 打卡
- 切換到「打卡」頁籤
- 點選「啟動攝影機」
- 面向鏡頭，確保畫面中恰好包含一張人臉
- 點選「立即打卡」執行辨識打卡

### 3. 查詢記錄
- 切換到「打卡記錄」頁籤
- 查看今日所有打卡記錄
- 上班時間 = 當日最早記錄
- 下班時間 = 當日最晚記錄

## 技術規格

- 人臉偵測：MediaPipe
- 人臉辨識：InsightFace (Buffalo_L)
- 特徵維度：512-D
- 辨識門檻：0.4
- 打卡冷卻：5 分鐘
- 資料庫：SQLite

## 專案結構

```
FaceAttendance/
├── src/
│   ├── main.py          # 程式進入點
│   ├── core/
│   │   ├── detector.py      # 人臉偵測
│   │   ├── recognizer.py    # 人臉辨識
│   │   └── database.py      # 資料庫操作
│   └── ui/
│       └── main_window.py   # GUI 主視窗
├── data/                # 資料目錄（自動建立）
├── config.yaml          # 系統設定
└── requirements.txt     # 依賴套件
```
