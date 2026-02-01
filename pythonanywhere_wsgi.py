# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/<your-username>/exam_duty_assigner'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the working directory
os.chdir(project_home)

# Import your Flask app
from app import app as application

# PythonAnywhere requires the WSGI application to be named 'application'
