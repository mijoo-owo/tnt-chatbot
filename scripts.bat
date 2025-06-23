@echo off
REM Create virtual environment if it doesn't exist
if not exist venv (
    python -m venv venv
)

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Go to app directory
cd app

REM Open browser (run in parallel)
start http://localhost:5000

REM Launch Streamlit app on port 5000
streamlit run app.py

pause

