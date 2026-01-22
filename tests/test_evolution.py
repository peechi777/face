import sys
import os
import numpy as np
import unittest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.database import Database
from core.recognizer import FaceRecognizer

class TestFeatureEvolution(unittest.TestCase):
    def setUp(self):
        # Use a temporary database
        self.db_path = "test_data/test_evolution.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = Database(self.db_path)
        self.recognizer = FaceRecognizer()
        
    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

    def test_evolution_math(self):
        """Test the mathematical correctness of evolution"""
        # Create two random normalized vectors
        v1 = np.random.rand(512).astype(np.float32)
        v1 = v1 / np.linalg.norm(v1)
        
        v2 = np.random.rand(512).astype(np.float32)
        v2 = v2 / np.linalg.norm(v2)
        
        rate = 0.1
        evolved = self.recognizer.evolve_feature(v1, v2, rate)
        
        # Expected calculation manually
        expected = (1 - rate) * v1 + rate * v2
        expected = expected / np.linalg.norm(expected)
        
        # Check if close
        self.assertTrue(np.allclose(evolved, expected, atol=1e-6))
        print("Math verification: PASS")

    def test_database_update(self):
        """Test database update persistence"""
        # 1. Create dummy employee
        emp_id = "TEST001"
        name = "Test User"
        v1 = np.ones(512, dtype=np.float32)
        v1 = v1 / np.linalg.norm(v1)
        
        self.db.add_employee(emp_id, name, v1)
        
        # 2. Get stored feature
        _, _, stored_v1 = self.db.get_employee(emp_id)
        self.assertTrue(np.allclose(v1, stored_v1))
        
        # 3. Create new feature (simulate slightly different face)
        v2 = np.ones(512, dtype=np.float32) * 0.5
        v2[0] = 1.0 # Make it different
        v2 = v2 / np.linalg.norm(v2)
        
        # 4. Evolve
        evolved = self.recognizer.evolve_feature(stored_v1, v2, rate=0.1)
        
        # 5. Update DB
        success = self.db.update_employee_feature(emp_id, evolved)
        self.assertTrue(success)
        
        # 6. Verify DB has new feature
        _, _, stored_new = self.db.get_employee(emp_id)
        
        # Should be equal to evolved
        self.assertTrue(np.allclose(evolved, stored_new))
        
        # Should NOT be equal to original v1
        self.assertFalse(np.allclose(v1, stored_new))
        
        print("Database update verification: PASS")

if __name__ == '__main__':
    unittest.main()
