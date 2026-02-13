; VenvStudio Inno Setup Script
[Setup]
AppName=VenvStudio
AppVersion=1.2.0
DefaultDirName={autopf}\VenvStudio
DefaultGroupName=VenvStudio
OutputDir=installer
OutputBaseFilename=VenvStudio_Setup_v1.2.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\VenvStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vs.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "vs.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\VenvStudio"; Filename: "{app}\VenvStudio.exe"
Name: "{autodesktop}\VenvStudio"; Filename: "{app}\VenvStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"

[Run]
Filename: "{app}\VenvStudio.exe"; Description: "Launch VenvStudio"; Flags: postinstall nowait skipifsilent
