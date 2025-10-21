@echo off
echo Running DistrictHeatingSim with error capture...
echo.
cd /d "%~dp0"
dist\DistrictHeatingSim\DistrictHeatingSim.exe 2>&1
echo.
echo.
echo Exit code: %ERRORLEVEL%
echo.
pause
