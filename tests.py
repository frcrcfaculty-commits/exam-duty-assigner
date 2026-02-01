import unittest
import os
from app import app, db, Faculty, Timetable, ExamSessions, DutyAssignments
from logic.parser import parse_department_csv
from logic.allocator import assign_invigilators

class ExamSystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory DB for tests
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_allocator_fairness(self):
        with app.app_context():
            # Create 3 faculty with different duty counts
            f1 = Faculty(name="Low Duties", department="CS", total_duties_assigned=0)
            f2 = Faculty(name="Medium Duties", department="IT", total_duties_assigned=5)
            f3 = Faculty(name="High Duties", department="EXTC", total_duties_assigned=10)
            db.session.add_all([f1, f2, f3])
            db.session.commit()
            
            # Create Exam
            exam = ExamSessions(date="2024-01-01", day_of_week="MONDAY", start_time="10.00am", end_time="11.00am", required_invigilators=2)
            db.session.add(exam)
            db.session.commit()
            
            # Run assignment - should pick f1 and f2 (Least duties first)
            result = assign_invigilators(exam.id)
            self.assertIn("Low Duties", result['assigned'])
            self.assertIn("Medium Duties", result['assigned'])
            self.assertNotIn("High Duties", result['assigned'])
            
            # Verify counts increased
            self.assertEqual(f1.total_duties_assigned, 1)
            self.assertEqual(f2.total_duties_assigned, 6)
            self.assertEqual(f3.total_duties_assigned, 10)

    def test_allocator_busy_check(self):
        with app.app_context():
            f1 = Faculty(name="Busy Person", department="CS", total_duties_assigned=0)
            f2 = Faculty(name="Free Person", department="IT", total_duties_assigned=0)
            db.session.add_all([f1, f2])
            db.session.commit()
            
            # Mark f1 as busy
            # Exam is 10-11am. Mark busy 9.45am-10.45am (overlap)
            t1 = Timetable(faculty_id=f1.id, day_of_week="MONDAY", time_slot="9.45am-10.45am", is_busy=True)
            db.session.add(t1)
            db.session.commit()
            
            exam = ExamSessions(date="2024-01-01", day_of_week="MONDAY", start_time="10.00am", end_time="11.00am", required_invigilators=1)
            db.session.add(exam)
            db.session.commit()
            
            result = assign_invigilators(exam.id)
            self.assertIn("Free Person", result['assigned'])
            self.assertNotIn("Busy Person", result['assigned'])

if __name__ == '__main__':
    unittest.main()
