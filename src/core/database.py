import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import numpy as np


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化資料庫表格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 員工表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                feature BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # 打卡記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL NOT NULL,
                photo BLOB,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        # 建立索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_attendance_timestamp 
            ON attendance_records(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_attendance_employee 
            ON attendance_records(employee_id, timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_employee(self, employee_id: str, name: str, feature: np.ndarray) -> bool:
        """新增員工"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            feature_blob = feature.tobytes()
            created_at = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO employees (employee_id, name, feature, created_at)
                VALUES (?, ?, ?, ?)
            ''', (employee_id, name, feature_blob, created_at))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_employee(self, employee_id: str) -> Optional[Tuple[str, str, np.ndarray]]:
        """取得員工資料"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT employee_id, name, feature FROM employees WHERE employee_id = ?
        ''', (employee_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            emp_id, name, feature_blob = row
            feature = np.frombuffer(feature_blob, dtype=np.float32)
            return emp_id, name, feature
        return None
    
    def get_all_employees(self) -> List[Tuple[str, str, np.ndarray]]:
        """取得所有員工"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT employee_id, name, feature FROM employees')
        rows = cursor.fetchall()
        conn.close()
        
        employees = []
        for emp_id, name, feature_blob in rows:
            feature = np.frombuffer(feature_blob, dtype=np.float32)
            employees.append((emp_id, name, feature))
        
        return employees
    
    def delete_employee(self, employee_id: str) -> bool:
        """刪除員工"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM employees WHERE employee_id = ?', (employee_id,))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception:
            return False
    
    def add_attendance_record(self, employee_id: str, name: str, 
                            confidence: float, photo: Optional[bytes] = None) -> bool:
        """新增打卡記錄"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO attendance_records 
                (employee_id, name, timestamp, confidence, photo)
                VALUES (?, ?, ?, ?, ?)
            ''', (employee_id, name, timestamp, confidence, photo))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def check_recent_attendance(self, employee_id: str, minutes: int = 5) -> bool:
        """檢查最近 N 分鐘內是否有打卡記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        time_threshold = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        
        cursor.execute('''
            SELECT COUNT(*) FROM attendance_records 
            WHERE employee_id = ? AND timestamp > ?
        ''', (employee_id, time_threshold))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_today_attendance(self) -> List[Tuple[str, str, str, str, float]]:
        """取得今日所有打卡記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        cursor.execute('''
            SELECT employee_id, name, timestamp, 
                   CASE 
                       WHEN timestamp = (
                           SELECT MIN(timestamp) FROM attendance_records r2 
                           WHERE r2.employee_id = attendance_records.employee_id 
                           AND DATE(r2.timestamp) = DATE(attendance_records.timestamp)
                       ) THEN '上班'
                       WHEN timestamp = (
                           SELECT MAX(timestamp) FROM attendance_records r2 
                           WHERE r2.employee_id = attendance_records.employee_id 
                           AND DATE(r2.timestamp) = DATE(attendance_records.timestamp)
                       ) THEN '下班'
                       ELSE '其他'
                   END as type,
                   confidence
            FROM attendance_records
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        ''', (today,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    
    def get_attendance_by_date_range(self, start_date: str, end_date: str) -> List[Tuple]:
        """取得指定日期範圍的打卡記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT employee_id, name, timestamp, confidence
            FROM attendance_records
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
