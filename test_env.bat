@echo off
set PYTHON_PATH=C:\Program Files\Python313
set PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%

REM Run the test script
"%PYTHON_PATH%\python.exe" test_image_processing.py
pause 