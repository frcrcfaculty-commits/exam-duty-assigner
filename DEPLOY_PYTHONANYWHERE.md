# Father Agnel - Exam Duty Assigner

## Deployment to PythonAnywhere (FREE)

### Step 1: Create PythonAnywhere Account
1. Go to https://www.pythonanywhere.com
2. Click "Start running Python online in less than a minute!"
3. Create a FREE account (no credit card needed)

### Step 2: Upload Your Files
1. After login, click on **"Files"** in the top menu
2. Create a new directory: `exam_duty_assigner`
3. Upload ALL files from this folder:
   - `app.py`
   - `database.py`
   - `requirements.txt`
   - `logic/` folder (with `parser.py` and `allocator.py`)
   - `templates/` folder (all HTML files)

### Step 3: Create Virtual Environment
1. Go to **"Consoles"** → Start a **"Bash"** console
2. Run these commands:
```bash
cd exam_duty_assigner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Configure Web App
1. Go to **"Web"** tab
2. Click **"Add a new web app"**
3. Select **"Manual configuration"** (NOT Flask)
4. Choose **Python 3.10**

### Step 5: Configure WSGI
1. In the Web tab, click the WSGI configuration file link
2. Delete everything and paste this (replace `<your-username>`):

```python
import sys
import os

project_home = '/home/<your-username>/exam_duty_assigner'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
```

3. Save the file

### Step 6: Set Virtual Environment Path
1. In the Web tab, find "Virtualenv" section
2. Enter: `/home/<your-username>/exam_duty_assigner/venv`

### Step 7: Reload and Test
1. Click the green **"Reload"** button
2. Visit: `https://<your-username>.pythonanywhere.com`

---

## Your App is Now LIVE! 🎉

The URL will be: `https://<your-username>.pythonanywhere.com`

### Important Notes:
- SQLite database is stored in `instance/exam_system.db`
- Free tier allows 1 web app
- App may sleep after 3 months of inactivity (just log in to wake it)
- Use the Export/Import feature to backup your data regularly

### Troubleshooting:
- Check **"Error log"** in the Web tab if something goes wrong
- Make sure all file paths use `/home/<your-username>/exam_duty_assigner/`
