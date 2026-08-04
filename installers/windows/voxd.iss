; VOXD Inno Setup installer script
; Build: iscc installers\windows\voxd.iss  (after running build-exe.cmd)

#define MyAppName "VOXD"
#ifndef MyAppVersion
#define MyAppVersion "1.0.2"
#endif
#define MyAppPublisher "VOXD contributors"
#define MyAppExeName "VOXD.exe"

[Setup]
AppId={{7A6E3C5F-9A2B-4C8D-8E1F-3B0A5D6E7F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\build\windows
OutputBaseFilename=VOXD-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupIconFile=..\..\assets\icons\voxd.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch VOXD at login"; GroupDescription: "Startup:"
Name: "runsetup"; Description: "Download the Whisper engine and model now (recommended, ~85 MB)"; GroupDescription: "First-run setup:"; Flags: checkedonce

[Files]
Source: "..\..\dist\VOXD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
; First-run setup: download prebuilt whisper-cli.exe + a Whisper model, verify,
; then write config. Runs during install (before the Finish page). A console
; window shows download progress. Skippable via the "runsetup" task.
Filename: "{app}\VOXD-setup.exe"; Parameters: "--prebuilt"; StatusMsg: "Setting up Whisper engine and model (this takes a few minutes)..."; Tasks: runsetup; Flags: runhidden

Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
    Log('VOXD installed successfully.');
end;
