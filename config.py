import os

# Base folder constants
BASE_FOLDER = 'D:/Uploader Transfer/aa-auto'  # Updated to match current computer
SCRIPTS_FOLDER = BASE_FOLDER
TEMPLATE_IMAGES_FOLDER = os.path.join(BASE_FOLDER, 'Templateimages')
DOWNLOAD_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Download')
OUTPUT_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Output')
CSV_FOLDER = os.path.join(BASE_FOLDER, 'printpanels', 'csv')
MOCKUP_FOLDER = os.path.join(BASE_FOLDER, 'Mockup')
BAGS_FOLDER = os.path.join(BASE_FOLDER, 'Bags & Tissues')

# Python executable path
PYTHON_PATH = "C:\\Program Files\\Python313\\python.exe"

# AWS S3 Configuration
BUCKET_NAME = 'compoundfoundry'

# Template dimensions
TEMPLATE_6FT_WIDTH = 2171.53
TEMPLATE_6FT_HEIGHT = 5285.94
TEMPLATE_15FT_WIDTH = 2171.53
TEMPLATE_15FT_HEIGHT = 13061.90 