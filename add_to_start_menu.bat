@echo off
echo Adding Atlas to your Start Menu...

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.Environment]::GetFolderPath('StartMenu') + '\Programs\Atlas.lnk'); $s.TargetPath = 'D:\Projects\atlas\start.bat'; $s.WorkingDirectory = 'D:\Projects\atlas'; $s.WindowStyle = 1; $s.Description = 'Launch Atlas'; $s.IconLocation = 'D:\Projects\atlas\frontend\public\atlas.ico'; $s.Save()"

echo Done. Search "Atlas" in the Start Menu.
pause
