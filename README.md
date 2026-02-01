# Father Agnel - Exam Duty Assigner

A Flask-based web application for automated exam invigilation duty assignment at Father Agnel College.

## Features

- **Faculty Management**: Add, edit, and manage faculty members with priorities and roles
- **Bulk Upload**: Import faculty lists from Excel/CSV files
- **Smart Timetable Parsing**: Automatically parse faculty timetables from various formats
- **Fair Duty Assignment**: Automated algorithm assigns duties fairly based on:
  - Faculty priorities (P1-P3)
  - Role exclusions (HODs, Principals, Coordinators)
  - Previous duty counts
- **Department-based Filtering**: Filter faculty by department
- **Data Export/Import**: Backup and restore data via JSON
- **Reset Options**: Reset all data or just exam duties (keep faculty)

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/frcrcfaculty-commits/exam-duty-assigner.git
cd exam-duty-assigner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Visit: **http://localhost:5000**

### Deployment (PythonAnywhere)

See [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md) for detailed deployment instructions.

## Project Structure

```
exam_invigilation_system/
├── app.py                 # Main Flask application
├── database.py            # SQLAlchemy models
├── requirements.txt       # Python dependencies
├── logic/
│   ├── parser.py          # Timetable parsing logic
│   └── allocator.py       # Duty assignment algorithm
├── templates/             # Jinja2 HTML templates
├── static/                # Static assets (CSS, images)
└── DEPLOY_PYTHONANYWHERE.md
```

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy
- **Database**: SQLite
- **Frontend**: Jinja2 templates, TailwindCSS (CDN)
- **Data Processing**: Pandas, openpyxl

## Authors

Gift for Merley Ma'am. Made by **Hansal Gandhi** and **Sherly Arockia**

## License

MIT License - Father Agnel College Internal Use
