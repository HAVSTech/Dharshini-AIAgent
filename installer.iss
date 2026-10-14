#define MyAppName "Dharshini Print Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "HAVS Tech"
#define MyAppExeName "Dharshini Print Manager.exe"

[Setup]
AppId={{D7B51C7D-9C6B-4A3A-A93D-6DAA3B1F0212}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Dharshini Print Manager
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=Dharshini-Print-Manager-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\Dharshini Print Manager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Dharshini Print Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Dharshini Print Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Dharshini Print Manager"; Flags: postinstall nowait skipifsilent
