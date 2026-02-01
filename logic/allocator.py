"""
Allocator module for assigning invigilators to exam sessions.
Respects priority levels (P1=Protected, P2=Moderate, P3=Available) and roles.
"""

from database import db, Faculty, Timetable, ExamSessions, DutyAssignments
import random
import re

def parse_time_to_minutes(time_str):
    """
    Parses strings like "8.45 am", "2.30 p.m.", "12 pm" into minutes from midnight.
    Returns None if parsing fails.
    """
    if not time_str:
        return None
    
    # Use regex to find digits and am/pm
    match = re.search(r'(\d+)(?::|\.)?(\d+)?\s*(a|p)m?', time_str.lower())
    if not match:
        return None
        
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)  # 'a' or 'p'
    
    if meridiem == 'p' and hour != 12:
        hour += 12
    if meridiem == 'a' and hour == 12:
        hour = 0
        
    return hour * 60 + minute


def check_overlap(start1, end1, start2, end2):
    """
    Checks if time range [start1, end1] overlaps with [start2, end2].
    Times are in minutes from midnight.
    """
    return max(start1, start2) < min(end1, end2)


def assign_invigilators(exam_id):
    """
    Assigns invigilators to a specific exam session based on:
    1. Availability (not busy during exam time)
    2. Role (only INVIGILATOR role, excludes COORDINATOR and SUPERVISOR)
    3. Priority (P3=Available first, P2=Moderate second, P1=Protected last)
    4. Fairness (least duties assigned first)
    """
    exam = ExamSessions.query.get(exam_id)
    if not exam:
        return {"error": "Exam not found"}

    # Parse Exam Times
    exam_start_min = parse_time_to_minutes(exam.start_time)
    exam_end_min = parse_time_to_minutes(exam.end_time)
    
    if exam_start_min is None or exam_end_min is None:
        return {"error": "Invalid exam time format"}

    # 1. Filter by Availability (busy status)
    busy_faculty_ids = set()
    
    busy_entries = Timetable.query.filter_by(day_of_week=exam.day_of_week, is_busy=True).all()
    
    for entry in busy_entries:
        if '-' in entry.time_slot:
            parts = entry.time_slot.split('-')
            slot_start = parse_time_to_minutes(parts[0])
            slot_end = parse_time_to_minutes(parts[1])
            
            if slot_start is not None and slot_end is not None:
                if check_overlap(exam_start_min, exam_end_min, slot_start, slot_end):
                    busy_faculty_ids.add(entry.faculty_id)

    # 2. Get Candidates
    # - NOT in busy list
    # - Role must be INVIGILATOR (exclude COORDINATOR, SUPERVISOR, HOD, PRINCIPAL)
    candidates = Faculty.query.filter(
        Faculty.id.notin_(busy_faculty_ids),
        Faculty.role == 'INVIGILATOR'
    ).all()
    
    print(f"[ALLOCATOR] Found {len(candidates)} available invigilators")
    
    # 3. Sort by Priority and Fairness
    # Priority order: P3 (Available) -> P2 (Moderate) -> P1 (Protected)
    # Within same priority: sort by duties ascending, with random shuffle for ties
    
    priority_order = {'P3': 0, 'P2': 1, 'P1': 2}
    
    random.shuffle(candidates)  # Randomize first for tie-breaking
    candidates.sort(key=lambda x: (
        priority_order.get(x.priority, 0),  # P3 first, P1 last
        x.total_duties_assigned              # Least duties first
    ))
    
    # 4. Assign required number
    required = exam.required_invigilators
    
    if len(candidates) < required:
        assigned_faculty = candidates  # Take everyone we have
        warning = f"Only {len(candidates)} invigilators available, required {required}"
    else:
        assigned_faculty = candidates[:required]
        warning = None
        
    # Save Assignments
    results = []
    for fac in assigned_faculty:
        existing = DutyAssignments.query.filter_by(exam_id=exam.id, faculty_id=fac.id).first()
        if not existing:
            new_assignment = DutyAssignments(exam_id=exam.id, faculty_id=fac.id)
            db.session.add(new_assignment)
            fac.total_duties_assigned += 1
        results.append(fac.name)
            
    db.session.commit()
    
    print(f"[ALLOCATOR] Assigned {len(results)} invigilators: {results}")
    
    return {
        "status": "success",
        "assigned": results,
        "warning": warning
    }
