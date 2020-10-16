set script_dir=%~dp0
set in_dir=%~dp1
set filename=%~n1
call %USERPROFILE%\anaconda3\Scripts\activate.bat
%USERPROFILE%\anaconda3\python.exe %script_dir%\remove_original.py %1 %in_dir%\cleaned-%filename%.csv
pause
