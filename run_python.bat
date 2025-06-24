@echo off
set PYTHON_PATH=C:\Program Files\Python313
set PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%

REM Run the Python script passed as an argument
"%PYTHON_PATH%\python.exe" %* 