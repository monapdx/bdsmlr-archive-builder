@echo off
echo Building archive...
bdsmlr-archive build --input exports\*.json --out output --download-media
echo.
echo Done!
pause