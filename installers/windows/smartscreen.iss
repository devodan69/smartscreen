; Inno Setup template for SmartScreen Windows installer
[Setup]
AppName=SmartScreen
AppVersion=0.1.0
DefaultDirName={autopf}\SmartScreen
DefaultGroupName=SmartScreen
OutputBaseFilename=smartscreen-windows-x64
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\SmartScreen\\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\\SmartScreen"; Filename: "{app}\\SmartScreen.exe"
Name: "{commondesktop}\\SmartScreen"; Filename: "{app}\\SmartScreen.exe"

[Run]
Filename: "{app}\\SmartScreen.exe"; Description: "Launch SmartScreen"; Flags: nowait postinstall skipifsilent
