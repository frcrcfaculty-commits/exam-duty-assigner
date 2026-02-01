import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    total_duties_assigned = db.Column(db.Integer, default=0)
    
    # Priority: P1=Protected (Senior), P2=Moderate, P3=Available (Default)
    priority = db.Column(db.String(10), default='P3')
    
    # Role: INVIGILATOR (default), COORDINATOR, SUPERVISOR, HOD, PRINCIPAL
    role = db.Column(db.String(20), default='INVIGILATOR')
    
    # Relationships
    duties = db.relationship('DutyAssignments', backref='faculty', lazy=True)
    timetable_entries = db.relationship('Timetable', backref='faculty', lazy=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # MONDAY, TUESDAY, etc.
    time_slot = db.Column(db.String(50), nullable=False)    # "8.45 am-9.45 am"
    is_busy = db.Column(db.Boolean, default=False)

class ExamSessions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    required_invigilators = db.Column(db.Integer, nullable=False)
    
    # Enhanced scheduling fields
    num_classrooms = db.Column(db.Integer, default=1)
    spare_invigilators = db.Column(db.Integer, default=0)
    exam_duration_hours = db.Column(db.Integer, default=1)  # 1, 2, or 3 hours
    
    # Relationships
    assignments = db.relationship('DutyAssignments', backref='exam_session', lazy=True)

class DutyAssignments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
