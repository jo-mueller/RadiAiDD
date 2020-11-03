set anaconda_dir=C:\Users\johan\anaconda3
set script_location=D:\Documents\Promotion\Projects\RadiAID

echo Checking packages

call "%anaconda_dir%\Scripts\activate.bat"
%anaconda_dir%\Scripts\pip.exe install pyserial
%anaconda_dir%\Scripts\pip.exe install pydicom
%anaconda_dir%\Scripts\pip.exe install coloredlogs

"%anaconda_dir%\python.exe" "%script_location%\Positioning_AssistantMAIN.py"
pause