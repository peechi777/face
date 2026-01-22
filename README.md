# 人臉辨識打卡系統 (Face Attendance System)

一個基於 Python 的離線人臉辨識打卡系統，支援員工註冊、即時打卡、活體偵測與工時統計。

## ✨ 主要功能

### 🔐 員工註冊
- 上傳證件照並自動提取人臉特徵
- 使用 InsightFace 提取 512 維特徵向量
- 支援員工資料管理（新增/刪除）

### ⏰ 智慧打卡
- **即時人臉辨識**：透過攝影機即時辨識員工身份
- **活體偵測**：眨眼偵測防止照片/影片打卡
- **多種打卡類型**：上班（綠色）、下班（紅色）、休息（黃色）
- **特徵演進**：系統會隨時間自動更新人臉特徵，適應外觀變化
- **冷卻機制**：防止短時間內重複打卡

### 📊 記錄查詢
- 日期範圍查詢
- 每日工時自動計算
- 打卡照片記錄
- 詳細打卡明細（時間、類型、信心度）

---

## 🚀 快速開始

### 系統需求
- Windows 10/11
- Python 3.10+
- 攝影機（用於打卡）

### 安裝步驟

1. **安裝 Python 依賴**
```bash
pip install -r requirements.txt
```

2. **執行對應的程式**

#### 方式一：獨立模組（推薦）
```bash
# 員工註冊系統（管理員使用）
run_register.bat

# 打卡系統（員工使用）
run_attendance.bat

# 記錄查詢系統（管理員/主管使用）
run_records.bat
```

#### 方式二：完整版（管理員使用）
```bash
# 包含所有功能的完整版
run.bat
```

---

## 📁 專案結構

```
d:\face\
├── run.bat                    # 啟動完整管理員版本
├── run_register.bat           # 啟動員工註冊系統
├── run_attendance.bat         # 啟動打卡系統
├── run_records.bat            # 啟動記錄查詢系統
├── config.yaml                # 系統設定檔
├── requirements.txt           # Python 套件依賴
├── README.md                  # 本檔案
│
├── src/
│   ├── main.py               # 原始入口（完整版）
│   ├── run_module.py         # 模組化入口
│   │
│   ├── core/                 # 核心邏輯
│   │   ├── database.py       # 資料庫管理（SQLite）
│   │   ├── detector.py       # 人臉偵測（MediaPipe）
│   │   ├── recognizer.py     # 人臉辨識（InsightFace）
│   │   └── liveness.py       # 活體偵測（眨眼偵測）
│   │
│   └── ui/                   # 使用者介面
│       └── main_window.py    # 所有 UI 視窗與元件
│
├── data/
│   └── attendance.db         # SQLite 資料庫
│
└── tests/
    └── test_evolution.py     # 特徵演進測試
```

---

## 🎯 核心模組說明

### 📦 Core 模組

#### `database.py` - 資料庫管理
- 員工資料 CRUD 操作
- 打卡記錄儲存與查詢
- 支援日期範圍查詢
- 自動計算工時

#### `detector.py` - 人臉偵測
- 使用 MediaPipe 偵測人臉
- 自動裁切人臉區域
- 確保畫面中只有一張人臉

#### `recognizer.py` - 人臉辨識
- 使用 InsightFace (buffalo_l) 模型
- 提取 512 維人臉特徵向量
- 餘弦相似度比對
- **特徵演進**：每次打卡後更新特徵 (rate=0.1)

#### `liveness.py` - 活體偵測
- 使用 MediaPipe FaceMesh
- 眨眼偵測（EAR 演算法）
- 防止照片/影片攻擊

---

## 🖥️ UI 視窗說明

### `RegistrationWindow` - 員工註冊視窗
- **左側面板**：員工資料輸入、證件照選擇
- **右側面板**：已註冊員工列表

### `AttendanceWindow` - 打卡視窗
- **打卡類型選擇**：
  - 🟢 上班 (Clock In)
  - 🔴 下班 (Clock Out)
  - 🟡 休息 (Break) + 時數設定
- **即時攝影機畫面**：顯示人臉框與活體偵測狀態
- **狀態提示**：打卡成功/失敗訊息 + 語音播報

### `RecordsWindow` - 記錄查詢視窗
- **日期選擇器**：查詢特定日期記錄
- **每日工時統計表**：顯示員工當日總工時
- **詳細打卡記錄表**：包含時間、類型、信心度、照片

---

## ⚙️ 設定檔說明 (`config.yaml`)

```yaml
database:
  path: "data/attendance.db"

camera:
  device_id: 0                # 攝影機 ID

face_detection:
  min_detection_confidence: 0.7

face_recognition:
  model: "buffalo_l"          # InsightFace 模型
  recognition_threshold: 0.5  # 辨識閾值

attendance:
  cooldown_minutes: 1         # 打卡冷卻時間（分鐘）
```

---

## 🎨 UI 設計特色

### 現代化深色主題
- 深色背景 (#2b2b2b) 減少眼睛疲勞
- 藍色強調色 (#4da3ff) 提升視覺層次
- 圓角設計 (6-8px) 更加柔和

### 大型切換按鈕
- **上班**：選中時變為綠色 (#28a745)
- **下班**：選中時變為紅色 (#dc3545)
- **休息**：選中時變為黃色 (#ffc107)
- 字體加大 (16px)、加粗，易於辨識

### 響應式互動
- 按鈕 Hover 效果
- 輸入框 Focus 高亮
- 表格交替行顏色

---

## 🔄 工作流程

### 1️⃣ 員工註冊流程
```
選擇證件照 → 偵測人臉 → 提取特徵 → 儲存到資料庫
```

### 2️⃣ 打卡流程
```
啟動攝影機 → 偵測人臉 → 眨眼驗證 → 選擇打卡類型 → 
辨識身份 → 檢查冷卻時間 → 記錄打卡 → 更新特徵 → 語音播報
```

### 3️⃣ 工時計算邏輯
```
上班 → 下班/休息 = 累加工時
範例：09:00 上班 → 12:00 休息 → 13:00 上班 → 18:00 下班
工時 = (12:00-09:00) + (18:00-13:00) = 8.0 小時
```

---

## 🛡️ 安全機制

1. **活體偵測**：防止使用照片/影片打卡
2. **冷卻機制**：同類型打卡需間隔 N 分鐘
3. **信心度記錄**：每次辨識都記錄信心度，可追溯
4. **照片存證**：每次打卡都儲存人臉照片

---

## 📝 資料庫結構

### `employees` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| employee_id | TEXT | 員工 ID (主鍵) |
| name | TEXT | 姓名 |
| feature | BLOB | 512 維特徵向量 |
| created_at | TEXT | 註冊時間 |

### `attendance_records` 表
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 自動遞增 ID |
| employee_id | TEXT | 員工 ID |
| name | TEXT | 姓名 |
| timestamp | TEXT | 打卡時間 |
| type | TEXT | 類型（上班/下班/休息） |
| duration | INTEGER | 休息時數 |
| confidence | REAL | 辨識信心度 |
| photo | BLOB | 打卡照片 |

---

## 🔧 技術棧

- **GUI**: PySide6 (Qt for Python)
- **人臉偵測**: MediaPipe
- **人臉辨識**: InsightFace (buffalo_l)
- **活體偵測**: MediaPipe FaceMesh
- **資料庫**: SQLite3
- **影像處理**: OpenCV, PIL
- **語音播報**: Windows PowerShell TTS

---

## 📌 注意事項

1. **首次執行**會自動下載 InsightFace 模型（約 500MB）
2. **攝影機權限**：請確保 Python 有攝影機存取權限
3. **光線條件**：建議在光線充足環境下使用
4. **人臉角度**：請正面面向攝影機
5. **資料備份**：定期備份 `data/attendance.db`

---

## 🐛 常見問題

### Q: 程式啟動後卡住？
A: 首次啟動會下載模型，請耐心等待。若持續卡住，請檢查網路連線。

### Q: 辨識失敗率高？
A: 請調整 `config.yaml` 中的 `recognition_threshold`（降低閾值）。

### Q: 活體偵測太敏感？
A: 請確保光線充足，並面向攝影機眨眼。

### Q: 工時計算不正確？
A: 請確保打卡順序正確（上班 → 下班/休息）。

---

## 📄 授權

本專案僅供學習與內部使用。

---

## 👨‍💻 開發者

如需修改或擴充功能，請參考各模組的 docstring 註解。

**最後更新**: 2026-01-22
