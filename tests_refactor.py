import unittest
import os
from app import app, db, Faculty, Timetable, ExamSessions, DutyAssignments

class RefactorTestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_reset_data(self):
        with app.app_context():
            # Create some data
            f1 = Faculty(name="Test Fac", department="CS")
            db.session.add(f1)
            db.session.commit()
            self.assertEqual(Faculty.query.count(), 1)
            
            # Hit Reset Endpoint
            response = self.app.post('/reset', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            
            # Verify Empty
            self.assertEqual(Faculty.query.count(), 0)

if __name__ == '__main__':
    unittest.main()
