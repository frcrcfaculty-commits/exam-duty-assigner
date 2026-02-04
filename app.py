"""
Exam Invigilation Management System
A Flask-based web tool to assign exam duties fairly.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from database import db, init_db, Faculty, ExamSessions, DutyAssignments, Timetable
from logic.parser import parse_department_file
from logic.allocator import assign_invigilators
from datetime import datetime
import os
import random
import json

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_key_for_demo_change_in_production'

# Initialize Database
init_db(app)

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Dashboard - Fairness Leaderboard"""
    faculty_list = Faculty.query.order_by(Faculty.total_duties_assigned.asc()).all()
    return render_template('index.html', faculty=faculty_list)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload Department Timetable Files (CSV or Excel)"""
    if request.method == 'POST':
        files = request.files.getlist('files')
        
        # Debug: Log what we received
        print(f"[DEBUG] Received {len(files)} file(s)")
        for f in files:
            print(f"[DEBUG] File: '{f.filename}', Content-Type: {f.content_type}")
        
        if not files or all(f.filename == '' for f in files):
            flash("No files selected. Please choose at least one file.", "error")
            return redirect(url_for('upload'))
        
        success_count = 0
        error_messages = []
        
        for file in files:
            if file and file.filename:
                # Check file extension
                filename_lower = file.filename.lower()
                print(f"[DEBUG] Processing: {file.filename}")
                
                if filename_lower.endswith('.csv') or filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
                    # Ensure uploads directory exists
                    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save file temporarily
                    filepath = os.path.join(upload_dir, file.filename)
                    file.save(filepath)
                    print(f"[DEBUG] Saved to: {filepath}")
                    
                    # Parse the file
                    try:
                        result = parse_department_file(filepath)
                        print(f"[DEBUG] Parse result: {result}")
                        if result:
                            success_count += 1
                    except Exception as e:
                        import traceback
                        print(f"[DEBUG] Parse error: {traceback.format_exc()}")
                        error_messages.append(f"{file.filename}: {str(e)}")
                    finally:
                        # Always cleanup temp file
                        if os.path.exists(filepath):
                            os.remove(filepath)
                else:
                    error_messages.append(f"{file.filename}: Unsupported format. Use .csv, .xlsx, or .xls")
        
        # Show feedback
        if success_count > 0:
            flash(f"Successfully parsed {success_count} file(s).", "success")
        
        for err in error_messages:
            flash(f"Error: {err}", "error")
        
        if success_count == 0 and not error_messages:
            flash("No valid files were processed.", "warning")
            
        return redirect(url_for('index'))
        
    return render_template('upload.html')


@app.route('/reset', methods=['POST'])
def reset_data():
    """Clear all data from the database (POST method)"""
    try:
        DutyAssignments.query.delete()
        Timetable.query.delete()
        ExamSessions.query.delete()
        Faculty.query.delete()
        db.session.commit()
        flash("All data has been cleared successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing data: {str(e)}", "error")
    return redirect(url_for('index'))


@app.route('/reset-confirm')
def reset_confirm():
    """Show reset confirmation page"""
    return render_template('reset_confirm.html')


@app.route('/do-reset')
def do_reset():
    """Actually perform the reset (called from confirmation page)"""
    try:
        DutyAssignments.query.delete()
        Timetable.query.delete()
        ExamSessions.query.delete()
        Faculty.query.delete()
        db.session.commit()
        flash("All data has been cleared successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing data: {str(e)}", "error")
    return redirect(url_for('index'))


@app.route('/force-reset')
def force_reset():
    """Force reset via GET request (legacy support)"""
    return redirect(url_for('reset_confirm'))


@app.route('/reset-duties-confirm')
def reset_duties_confirm():
    """Show reset duties confirmation page"""
    return render_template('reset_duties_confirm.html')


@app.route('/do-reset-duties')
def do_reset_duties():
    """Reset only exam duties (keeps faculty list)"""
    try:
        DutyAssignments.query.delete()
        ExamSessions.query.delete()
        # Reset duty count on faculty
        Faculty.query.update({Faculty.total_duties_assigned: 0})
        db.session.commit()
        flash("Exam duties and sessions cleared. Faculty list preserved.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing duties: {str(e)}", "error")
    return redirect(url_for('index'))


@app.route('/generate_dummy', methods=['POST'])
def generate_dummy():
    """Generate dummy data for testing the fairness algorithm"""
    names = ["Dr. Alice Smith", "Dr. Bob Johnson", "Prof. Charlie Brown", 
             "Dr. David Lee", "Prof. Eve Williams", "Dr. Frank Miller",
             "Prof. Grace Davis", "Dr. Heidi Garcia", "Prof. Ivan Martinez", 
             "Dr. Judy Anderson"]
    departments = ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil"]
    
    added_count = 0
    for name in names:
        if not Faculty.query.filter_by(name=name).first():
            duty_count = random.randint(0, 5)
            f = Faculty(
                name=name, 
                department=random.choice(departments), 
                total_duties_assigned=duty_count
            )
            db.session.add(f)
            added_count += 1
    
    db.session.commit()
    
    # Create some busy slots for testing
    all_faculty = Faculty.query.all()
    busy_count = 0
    for faculty in all_faculty:
        # 30% chance to be busy on Monday morning
        if random.random() < 0.3:
            existing = Timetable.query.filter_by(
                faculty_id=faculty.id, 
                day_of_week="MONDAY", 
                time_slot="8.45am-9.45am"
            ).first()
            if not existing:
                t = Timetable(
                    faculty_id=faculty.id, 
                    day_of_week="MONDAY", 
                    time_slot="8.45am-9.45am", 
                    is_busy=True
                )
                db.session.add(t)
                busy_count += 1
    
    db.session.commit()
    
    flash(f"Generated {added_count} faculty members with {busy_count} busy slots.", "success")
    return redirect(url_for('index'))


@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    """Schedule an exam and auto-assign invigilators"""
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        exam_duration = request.form.get('exam_duration', '1')
        required_str = request.form.get('required_invigilators')
        num_classrooms_str = request.form.get('num_classrooms', '1')
        spare_str = request.form.get('spare_invigilators', '0')
        
        # Validation
        if not date_str or not start_time or not required_str:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('schedule'))
        
        try:
            required = int(required_str)
            num_classrooms = int(num_classrooms_str) if num_classrooms_str else 1
            spare = int(spare_str) if spare_str else 0
            duration = float(exam_duration) if exam_duration else 1.0
            if required < 1:
                raise ValueError("Required invigilators must be at least 1")
            if num_classrooms < 1:
                raise ValueError("Classrooms must be at least 1")
            if spare < 0:
                raise ValueError("Spare invigilators cannot be negative")
        except ValueError as e:
            flash(f"Invalid input: {str(e)}. All numeric fields must be valid.", "error")
            return redirect(url_for('schedule'))
        
        # Determine day of week from date
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_week = dt.strftime('%A').upper()
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('schedule'))
        
        # Use provided end_time or calculate from start + duration
        if not end_time:
            end_time = start_time  # Fallback
        
        # Total invigilators needed = required + spare
        total_needed = required + spare
            
        # Create exam session
        exam = ExamSessions(
            date=date_str,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            required_invigilators=total_needed,
            num_classrooms=num_classrooms,
            spare_invigilators=spare
        )
        db.session.add(exam)
        db.session.commit()
        
        # Auto-assign invigilators
        result = assign_invigilators(exam.id)
        
        if "error" in result:
            flash(f"Assignment error: {result['error']}", "error")
        elif result.get("warning"):
            flash(result["warning"], "warning")
        else:
            flash(f"Successfully assigned {len(result.get('assigned', []))} invigilators!", "success")
            
        return redirect(url_for('result', exam_id=exam.id))
        
    return render_template('schedule.html')


@app.route('/result/<int:exam_id>')
def result(exam_id):
    """View assignment results for a specific exam"""
    exam = ExamSessions.query.get_or_404(exam_id)
    assignments = DutyAssignments.query.filter_by(exam_id=exam.id).all()
    assigned_faculty = [a.faculty for a in assignments]
    
    return render_template('result.html', exam=exam, assigned_faculty=assigned_faculty, 
                         now=datetime.now().strftime('%d-%b-%Y %I:%M %p'))


@app.route('/result/<int:exam_id>/export')
def export_duty_sheet(exam_id):
    """Export duty sheet as Excel file"""
    import io
    try:
        import pandas as pd
    except ImportError:
        flash("pandas is required for Excel export", "error")
        return redirect(url_for('result', exam_id=exam_id))
    
    exam = ExamSessions.query.get_or_404(exam_id)
    assignments = DutyAssignments.query.filter_by(exam_id=exam.id).all()
    assigned_faculty = [a.faculty for a in assignments]
    
    # Create DataFrame
    data = []
    for i, staff in enumerate(assigned_faculty, 1):
        data.append({
            'Sr. No.': i,
            'Name of the Faculty': staff.name,
            'Room Number': '',
            'Signature': ''
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Duty Sheet', index=False)
    output.seek(0)
    
    filename = f"Duty_Sheet_{exam.date}_{exam.start_time.replace('.', '_')}.xlsx"
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/faculty')
def faculty_list():
    """Faculty management page - assign priorities and roles"""
    faculty = Faculty.query.order_by(Faculty.name.asc()).all()
    # Get unique departments for filter dropdown
    departments = sorted(set(f.department for f in faculty))
    return render_template('faculty.html', faculty=faculty, departments=departments)


@app.route('/faculty/<int:faculty_id>/update', methods=['POST'])
def faculty_update(faculty_id):
    """API endpoint to update faculty department, priority and role"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        data = request.get_json()
        
        if 'department' in data:
            dept = str(data['department']).strip()
            if dept:
                faculty.department = dept
        
        if 'priority' in data:
            if data['priority'] in ['P1', 'P2', 'P3']:
                faculty.priority = data['priority']
            else:
                return jsonify({'success': False, 'error': 'Invalid priority value'}), 400
        
        if 'role' in data:
            if data['role'] in ['INVIGILATOR', 'COORDINATOR', 'SUPERVISOR', 'HOD', 'PRINCIPAL']:
                faculty.role = data['role']
            else:
                return jsonify({'success': False, 'error': 'Invalid role value'}), 400
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/faculty/add', methods=['POST'])
def add_faculty_manual():
    """Manually add a single faculty member"""
    name = request.form.get('name', '').strip()
    department = request.form.get('department', 'General').strip()
    
    if not name or len(name) < 2:
        flash("Please enter a valid name.", "error")
        return redirect(url_for('faculty_list'))
    
    # Check if already exists
    existing = Faculty.query.filter(Faculty.name.ilike(name)).first()
    if existing:
        flash(f"Faculty '{name}' already exists.", "warning")
        return redirect(url_for('faculty_list'))
    
    try:
        new_faculty = Faculty(
            name=name,
            department=department or "General",
            priority='P3',
            role='INVIGILATOR',
            total_duties_assigned=0
        )
        db.session.add(new_faculty)
        db.session.commit()
        flash(f"Successfully added {name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding faculty: {str(e)}", "error")
    
    return redirect(url_for('faculty_list'))


@app.route('/faculty/bulk-upload', methods=['POST'])
def bulk_upload_employees():
    """Bulk upload employees from CSV/Excel file - handles complex formats"""
    import pandas as pd
    import re
    
    file = request.files.get('employee_file')
    if not file or file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('faculty_list'))
    
    original_filename = file.filename
    filename = file.filename.lower()
    print(f"[BULK UPLOAD] Processing file: {original_filename}")
    
    try:
        all_names = set()  # Collect all names from all sheets
        
        if filename.endswith('.csv'):
            # For CSV, read normally
            df = pd.read_csv(file)
            all_names.update(extract_names_from_df(df))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # For Excel, try all sheets
            xl = pd.ExcelFile(file)
            print(f"[BULK UPLOAD] Sheets found: {xl.sheet_names}")
            
            for sheet_name in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                print(f"[BULK UPLOAD] Processing sheet: {sheet_name}, shape: {df.shape}")
                names = extract_names_from_df(df)
                print(f"[BULK UPLOAD] Found {len(names)} names in {sheet_name}")
                all_names.update(names)
        else:
            flash("Please upload a CSV or Excel file.", "error")
            return redirect(url_for('faculty_list'))
        
        print(f"[BULK UPLOAD] Total unique names found: {len(all_names)}")
        
        # Add to database
        added_count = 0
        skipped_count = 0
        
        for name in all_names:
            # Check if already exists
            existing = Faculty.query.filter(Faculty.name.ilike(name)).first()
            if existing:
                skipped_count += 1
                continue
            
            new_faculty = Faculty(
                name=name,
                department="General",
                priority='P3',
                role='INVIGILATOR',
                total_duties_assigned=0
            )
            db.session.add(new_faculty)
            added_count += 1
        
        db.session.commit()
        print(f"[BULK UPLOAD] Added: {added_count}, Skipped: {skipped_count}")
        
        if added_count > 0:
            flash(f"Successfully added {added_count} employees. Skipped {skipped_count} duplicates.", "success")
        else:
            flash(f"No new employees added. {skipped_count} were duplicates.", "warning")
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[BULK UPLOAD] Error: {traceback.format_exc()}")
        flash(f"Error processing file: {str(e)}", "error")
    
    return redirect(url_for('faculty_list'))


def extract_names_from_df(df):
    """Extract faculty names from a dataframe with flexible format detection"""
    import re
    names = set()
    
    # Patterns that indicate a faculty name
    title_patterns = [
        r'^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.|Shri|Smt)\s*',  # Titles
    ]
    
    # Patterns to skip (headers, numbers, etc.)
    skip_patterns = [
        r'^(name|faculty|emp|employee|staff|teaching|non-teaching|sr|signature|department)',
        r'^\d+$',  # Pure numbers
        r'^unnamed',  # Pandas unnamed columns
        r'^(nan|none|null)$',
    ]
    
    # Scan all cells in the dataframe
    for col in df.columns:
        for val in df[col].dropna():
            text = str(val).strip()
            
            # Skip if too short
            if len(text) < 3:
                continue
            
            # Skip if matches skip patterns
            text_lower = text.lower()
            if any(re.match(p, text_lower) for p in skip_patterns):
                continue
            
            # Skip if pure number or has too many numbers
            if re.match(r'^\d+', text) and not re.search(r'[a-zA-Z]{3,}', text):
                continue
            
            # Accept if has a title prefix (Dr., Prof., etc.)
            if any(re.match(p, text, re.IGNORECASE) for p in title_patterns):
                names.add(text)
                continue
            
            # Accept if looks like a name (has letters, reasonable length)
            if re.match(r'^[A-Za-z.\s\']+$', text) and len(text) >= 5 and ' ' in text or '.' in text:
                names.add(text)
    
    return names



@app.route('/faculty/template')
def download_employee_template():
    """Download sample CSV template for bulk employee upload"""
    import io
    
    csv_content = """Name,Department
Dr. John Smith,Computer Science
Prof. Jane Doe,Information Technology
Mr. Robert Brown,Administration
Mrs. Alice Wilson,Electronics
"""
    
    output = io.BytesIO()
    output.write(csv_content.encode('utf-8'))
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=employee_template.csv'}
    )


@app.route('/export')
def export_data():
    """Export all data as JSON for backup"""
    data = {
        'export_date': datetime.now().isoformat(),
        'version': '1.0',
        'faculty': [],
        'timetable': [],
        'exam_sessions': [],
        'duty_assignments': []
    }
    
    for f in Faculty.query.all():
        data['faculty'].append({
            'id': f.id,
            'name': f.name,
            'department': f.department,
            'total_duties_assigned': f.total_duties_assigned,
            'priority': f.priority,
            'role': f.role
        })
    
    for t in Timetable.query.all():
        data['timetable'].append({
            'id': t.id,
            'faculty_id': t.faculty_id,
            'day_of_week': t.day_of_week,
            'time_slot': t.time_slot,
            'is_busy': t.is_busy
        })
    
    for e in ExamSessions.query.all():
        data['exam_sessions'].append({
            'id': e.id,
            'date': e.date,
            'day_of_week': e.day_of_week,
            'start_time': e.start_time,
            'end_time': e.end_time,
            'required_invigilators': e.required_invigilators,
            'num_classrooms': e.num_classrooms,
            'spare_invigilators': e.spare_invigilators,
            'exam_duration_hours': getattr(e, 'exam_duration_hours', 1)
        })
    
    for d in DutyAssignments.query.all():
        data['duty_assignments'].append({
            'id': d.id,
            'exam_id': d.exam_id,
            'faculty_id': d.faculty_id
        })
    
    filename = f"father_agnel_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        json.dumps(data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/import', methods=['GET', 'POST'])
def import_data():
    """Import data from JSON backup"""
    if request.method == 'POST':
        file = request.files.get('backup_file')
        if not file or not file.filename.endswith('.json'):
            flash("Please upload a valid JSON backup file.", "error")
            return redirect(url_for('import_data'))
        
        try:
            data = json.load(file)
            
            # Clear existing data
            DutyAssignments.query.delete()
            Timetable.query.delete()
            ExamSessions.query.delete()
            Faculty.query.delete()
            db.session.commit()
            
            # Import faculty
            for f in data.get('faculty', []):
                faculty = Faculty(
                    id=f['id'],
                    name=f['name'],
                    department=f['department'],
                    total_duties_assigned=f.get('total_duties_assigned', 0),
                    priority=f.get('priority', 'P3'),
                    role=f.get('role', 'INVIGILATOR')
                )
                db.session.add(faculty)
            
            db.session.commit()
            
            # Import timetable
            for t in data.get('timetable', []):
                timetable = Timetable(
                    id=t['id'],
                    faculty_id=t['faculty_id'],
                    day_of_week=t['day_of_week'],
                    time_slot=t['time_slot'],
                    is_busy=t.get('is_busy', True)
                )
                db.session.add(timetable)
            
            db.session.commit()
            
            # Import exam sessions
            for e in data.get('exam_sessions', []):
                exam = ExamSessions(
                    id=e['id'],
                    date=e['date'],
                    day_of_week=e['day_of_week'],
                    start_time=e['start_time'],
                    end_time=e['end_time'],
                    required_invigilators=e['required_invigilators'],
                    num_classrooms=e.get('num_classrooms', 1),
                    spare_invigilators=e.get('spare_invigilators', 0)
                )
                db.session.add(exam)
            
            db.session.commit()
            
            # Import duty assignments
            for d in data.get('duty_assignments', []):
                assignment = DutyAssignments(
                    id=d['id'],
                    exam_id=d['exam_id'],
                    faculty_id=d['faculty_id']
                )
                db.session.add(assignment)
            
            db.session.commit()
            
            flash(f"Successfully imported {len(data.get('faculty', []))} faculty, {len(data.get('exam_sessions', []))} exams.", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Import error: {str(e)}", "error")
            return redirect(url_for('import_data'))
    
    return render_template('import.html')


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Ensure uploads directory exists
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Run the development server
    print("=" * 60)
    print("Father Agnel - Exam Duty Assigner")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)

