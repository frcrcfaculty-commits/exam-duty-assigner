"""
Parser for Department Timetable Files
Handles CSV, Excel (.xlsx, .xls), and Word (.docx) files
"""

import pandas as pd
from database import db, Faculty, Timetable

def parse_department_file(filepath, department_name=None):
    """
    Parses a timetable file and updates the database.
    
    Supports these formats:
    1. Simple Table Format: Columns like Professor, Department, Day, Time
    2. Block Format: "NAME OF THE FACULTY" markers with day rows
    3. Word Document (.docx): Tables with faculty initials in timetable grids
    
    For Excel files with multiple sheets, each sheet is processed.
    """
    
    faculty_count = 0
    timetable_count = 0
    
    try:
        # Handle Word documents
        if filepath.lower().endswith('.docx'):
            print(f"[PARSER] Processing Word document")
            fc, tc = _parse_docx_timetable(filepath, department_name)
            faculty_count += fc
            timetable_count += tc
            
        elif filepath.lower().endswith('.xlsx') or filepath.lower().endswith('.xls'):
            # Excel file - process all sheets
            xl = pd.ExcelFile(filepath)
            for sheet_name in xl.sheet_names:
                print(f"[PARSER] Processing sheet: {sheet_name}")
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                
                # Detect format based on column names
                columns_lower = [str(c).lower() for c in df.columns]
                
                if any('professor' in c or 'faculty' in c or 'name' in c for c in columns_lower):
                    # Simple table format
                    print(f"[PARSER] Detected SIMPLE TABLE format")
                    fc, tc = _parse_simple_table(df, department_name)
                else:
                    # Block format - reload without header
                    df = pd.read_excel(filepath, header=None, sheet_name=sheet_name)
                    dept = department_name or sheet_name
                    fc, tc = _parse_dataframe(df, dept)
                
                faculty_count += fc
                timetable_count += tc
        else:
            # CSV file
            df = pd.read_csv(filepath)
            columns_lower = [str(c).lower() for c in df.columns]
            
            if any('professor' in c or 'faculty' in c or 'name' in c for c in columns_lower):
                fc, tc = _parse_simple_table(df, department_name)
            else:
                df = pd.read_csv(filepath, header=None)
                import os
                dept = department_name or os.path.splitext(os.path.basename(filepath))[0]
                fc, tc = _parse_dataframe(df, dept)
            
            faculty_count += fc
            timetable_count += tc
            
    except Exception as e:
        print(f"[PARSER] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    print(f"[PARSER] Total: {faculty_count} faculty, {timetable_count} timetable entries")
    return faculty_count > 0 or timetable_count > 0


def _parse_docx_timetable(filepath, department_name=None):
    """
    Parses a Word document (.docx) containing timetable tables.
    Extracts faculty initials/names and their busy time slots.
    """
    try:
        from docx import Document
    except ImportError:
        print("[PARSER] python-docx not installed. Run: pip install python-docx")
        return 0, 0
    
    faculty_count = 0
    timetable_count = 0
    faculty_set = set()  # Track unique faculty initials
    
    doc = Document(filepath)
    print(f"[PARSER] Found {len(doc.tables)} tables in document")
    
    days_list = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
    
    for table_idx, table in enumerate(doc.tables):
        if len(table.rows) < 3:
            continue
            
        print(f"[PARSER] Processing table {table_idx + 1}")
        
        # Try to extract time slots from header row (usually row 2)
        time_slots = {}
        header_row_idx = 2
        if len(table.rows) > header_row_idx:
            for col_idx, cell in enumerate(table.rows[header_row_idx].cells):
                cell_text = cell.text.strip()
                if 'a.m' in cell_text.lower() or 'p.m' in cell_text.lower():
                    # Normalize time format
                    time_str = cell_text.replace('\n', ' ').strip()
                    time_slots[col_idx] = time_str
        
        # Process data rows (look for day names)
        for row_idx, row in enumerate(table.rows):
            if row_idx < 3:  # Skip header rows
                continue
                
            # Check first cells for day name
            first_cell = row.cells[0].text.strip().upper()
            day_name = None
            for day in days_list:
                if day in first_cell:
                    day_name = day
                    break
            
            if not day_name:
                continue
            
            # Look for faculty initials in cells (usually 2-4 uppercase letters)
            for col_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                
                # Skip empty, breaks, room numbers, etc.
                if not cell_text or 'break' in cell_text.lower():
                    continue
                if cell_text.startswith('B') and '-' in cell_text:  # Room number like B1-208
                    continue
                if day_name in cell_text.upper():  # Skip day name cells
                    continue
                    
                # Extract faculty initials (2-4 uppercase letters)
                lines = cell_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Check if it looks like faculty initials
                    if len(line) >= 2 and len(line) <= 5 and line.isupper() and line.isalpha():
                        faculty_initial = line
                        
                        if faculty_initial not in faculty_set:
                            # Create faculty record
                            existing = Faculty.query.filter_by(name=faculty_initial).first()
                            if not existing:
                                dept = department_name or "General"
                                faculty = Faculty(
                                    name=faculty_initial, 
                                    department=dept, 
                                    total_duties_assigned=0
                                )
                                db.session.add(faculty)
                                db.session.commit()
                                faculty_count += 1
                                print(f"[PARSER] Created faculty: {faculty_initial}")
                            faculty_set.add(faculty_initial)
                        
                        # Add timetable entry if we have time slot info
                        time_str = time_slots.get(col_idx, "Unknown")
                        faculty_obj = Faculty.query.filter_by(name=faculty_initial).first()
                        if faculty_obj:
                            existing_tt = Timetable.query.filter_by(
                                faculty_id=faculty_obj.id,
                                day_of_week=day_name,
                                time_slot=time_str
                            ).first()
                            
                            if not existing_tt:
                                tt = Timetable(
                                    faculty_id=faculty_obj.id,
                                    day_of_week=day_name,
                                    time_slot=time_str,
                                    is_busy=True
                                )
                                db.session.add(tt)
                                timetable_count += 1
    
    db.session.commit()
    print(f"[PARSER] DOCX: {faculty_count} faculty, {timetable_count} timetable entries")
    return faculty_count, timetable_count


def _parse_simple_table(df, department_override=None):
    """
    Parses a simple table format with columns like:
    Professor | Department | Subject | Day | Busy Time
    """
    faculty_count = 0
    timetable_count = 0
    
    # Find column mappings (case-insensitive)
    columns_lower = {str(c).lower(): c for c in df.columns}
    
    name_col = None
    dept_col = None
    day_col = None
    time_col = None
    
    for col_lower, col_orig in columns_lower.items():
        if 'professor' in col_lower or 'faculty' in col_lower or col_lower == 'name':
            name_col = col_orig
        elif 'department' in col_lower or 'dept' in col_lower:
            dept_col = col_orig
        elif 'day' in col_lower:
            day_col = col_orig
        elif 'time' in col_lower or 'busy' in col_lower:
            time_col = col_orig
    
    print(f"[PARSER] Columns: name={name_col}, dept={dept_col}, day={day_col}, time={time_col}")
    
    if not name_col:
        print("[PARSER] ERROR: No name/professor column found")
        return 0, 0
    
    for _, row in df.iterrows():
        name = str(row.get(name_col, '')).strip()
        if not name or name.lower() == 'nan':
            continue
        
        department = department_override or (str(row.get(dept_col, 'General')).strip() if dept_col else 'General')
        if department.lower() == 'nan':
            department = 'General'
        
        # Get or create faculty
        faculty = Faculty.query.filter_by(name=name).first()
        if not faculty:
            faculty = Faculty(name=name, department=department, total_duties_assigned=0)
            db.session.add(faculty)
            db.session.commit()
            faculty_count += 1
            print(f"[PARSER] Created faculty: {name} ({department})")
        
        # Add timetable entry if day and time are present
        if day_col and time_col:
            day = str(row.get(day_col, '')).strip().upper()
            time_str = str(row.get(time_col, '')).strip()
            
            if day and time_str and day.lower() != 'nan' and time_str.lower() != 'nan':
                # Check if entry exists
                existing = Timetable.query.filter_by(
                    faculty_id=faculty.id,
                    day_of_week=day,
                    time_slot=time_str
                ).first()
                
                if not existing:
                    tt = Timetable(
                        faculty_id=faculty.id,
                        day_of_week=day,
                        time_slot=time_str,
                        is_busy=True
                    )
                    db.session.add(tt)
                    timetable_count += 1
    
    db.session.commit()
    print(f"[PARSER] Simple table: {faculty_count} faculty, {timetable_count} timetable entries")
    return faculty_count, timetable_count




def _parse_dataframe(df, department):
    """
    Parses a single DataFrame (one sheet) and extracts faculty timetables.
    Returns (faculty_count, timetable_count)
    """
    faculty_count = 0
    timetable_count = 0
    
    i = 0
    total_rows = len(df)
    days_list = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    
    print(f"[PARSER] DataFrame has {total_rows} rows")
    
    while i < total_rows:
        row = df.iloc[i]
        
        # Look for "NAME OF THE FACULTY" - check columns 1-3 (B, C, D)
        found_marker = False
        marker_col = None
        
        for col_idx in range(min(4, len(row))):
            cell_val = str(row[col_idx]).strip().upper() if pd.notna(row[col_idx]) else ""
            if "NAME OF THE FACULTY" in cell_val:
                found_marker = True
                marker_col = col_idx
                break
        
        if found_marker:
            # Try to find the faculty name - usually 2 columns after the marker
            faculty_name = None
            for offset in [2, 1, 3]:  # Try different offsets
                check_col = marker_col + offset
                if check_col < len(row):
                    val = row[check_col]
                    if pd.notna(val) and str(val).strip() and str(val).strip().upper() != "NAN":
                        faculty_name = str(val).strip()
                        break
            
            if not faculty_name:
                print(f"[PARSER] Row {i}: Found marker but no faculty name")
                i += 1
                continue
            
            print(f"[PARSER] Row {i}: Found faculty: {faculty_name}")
            
            # Check if faculty already exists
            faculty = Faculty.query.filter_by(name=faculty_name).first()
            if not faculty:
                faculty = Faculty(name=faculty_name, department=department, total_duties_assigned=0)
                db.session.add(faculty)
                db.session.commit()
                faculty_count += 1
                print(f"[PARSER] Created new faculty: {faculty_name} ({department})")
            else:
                print(f"[PARSER] Faculty already exists: {faculty_name}")
            
            # Next row should have time slots
            time_header_idx = i + 1
            if time_header_idx >= total_rows:
                i += 1
                continue
                
            time_row = df.iloc[time_header_idx]
            
            # Build time slot map: column_index -> time_string
            time_map = {}
            for col_idx in range(len(time_row)):
                val = time_row[col_idx]
                if pd.notna(val):
                    val_str = str(val).strip().lower()
                    # Check if it looks like a time (contains am or pm)
                    if 'am' in val_str or 'pm' in val_str:
                        time_map[col_idx] = str(time_row[col_idx]).strip()
            
            print(f"[PARSER] Time slots found at columns: {list(time_map.keys())}")
            
            # Read day rows (next 5-ish rows)
            current_row = time_header_idx + 1
            
            while current_row < total_rows:
                if current_row >= total_rows:
                    break
                    
                day_row = df.iloc[current_row]
                
                # Look for day name in first few columns
                day_name = None
                for col_idx in range(min(3, len(day_row))):
                    val = day_row[col_idx]
                    if pd.notna(val):
                        val_upper = str(val).strip().upper()
                        if val_upper in days_list:
                            day_name = val_upper
                            break
                
                if day_name:
                    # Process time slots for this day
                    for col_idx, time_str in time_map.items():
                        if col_idx < len(day_row):
                            cell_val = day_row[col_idx]
                            # If cell is not empty, faculty is busy
                            if pd.notna(cell_val):
                                cell_str = str(cell_val).strip()
                                if cell_str and cell_str.upper() != "NAN":
                                    # Check if entry already exists
                                    existing = Timetable.query.filter_by(
                                        faculty_id=faculty.id,
                                        day_of_week=day_name,
                                        time_slot=time_str
                                    ).first()
                                    
                                    if not existing:
                                        tt = Timetable(
                                            faculty_id=faculty.id,
                                            day_of_week=day_name,
                                            time_slot=time_str,
                                            is_busy=True
                                        )
                                        db.session.add(tt)
                                        timetable_count += 1
                    
                    current_row += 1
                else:
                    # No day found, might be end of block or empty row
                    # Check if next row might be a new faculty block
                    break
            
            i = current_row
            continue
        
        i += 1
    
    db.session.commit()
    return faculty_count, timetable_count
