import os
from pathlib import Path
import logging


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] : %(message)s:')

project_name = 'mlProject'

list_of_files = [
    ".github/workflows/.gitkeep"
    f"src/{project_name}/__init__.py",
    f"src/{project_name}/components/__init__.py",
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/common.py",
    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/configuration.py",
    f"src/{project_name}/pipeline/__init__.py",
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/entity/config_entity.py",
    f"src/{project_name}/constants/__init__.py",
    'config/config.yaml',
    "params.yaml",
    "schema.yaml",
    "main.py",
    "Dockerfile",
    "app.py",
    "requirements.txt",
    "setup.py",
    "research/trails.ipynb",
    "templates/index.html",
]

# creating files and folders
# first of all we'll itreate tgrough each and every object in list_of_files and create files and folders if Not exist
for file_path in list_of_files:
    filepath = Path(file_path)
    file_dir, filename = os.path.split(filepath)

    # Now that we've seperated the file directory and filename, we'll create  those file and folders

    if file_dir !="":
        os.makedirs(file_dir, exist_ok=True)
        logging.info(f"Creating directory: {file_dir} for the file: {filename}")

    # Creating the files if not exist
    if (not os.path.exists(filepath)) or os.path.getsize(filepath==0):
        with open(filepath, 'w') as f:
            pass
            logging.info(f"Creating empty directory: {filepath}")
    else:
        logging.info(f'{filename} already exist')

    



