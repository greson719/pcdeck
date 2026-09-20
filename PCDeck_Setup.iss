; Inno Setup Script for PCDeck Pro Windows Installer
; Designed for Microsoft Store Win32 & Standalone Distribution
; Author: Greshon Parichha

#define MyAppName "PCDeck"
#define MyAppVersion "2.7.1"
#define MyAppPublisher "Greshon Parichha"
#define MyAppURL "https://pcdeck.vercel.app"
#define MyAppExeName "PCDeck.exe"

[Setup]
; Unique application GUID for clean upgrades and uninstalls
AppId={{D37B4391-7C69-4BAF-9F22-540C68858A91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=mailto:gresonparichha719@gmail.com
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=PCDeck-Setup
SetupIconFile=app_icon.ico
WizardImageFile=WizardImage.bmp
WizardSmallImageFile=WizardSmallImage.bmp
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=no
RestartApplications=no
DisableWelcomePage=no
DisableDirPage=yes
UsePreviousAppDir=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Automatically start PCDeck when Windows boots"; GroupDescription: "Startup options:"

[Files]
Source: "PCDeck.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "PCDeck.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "PCDeck.apk"; DestDir: "{app}"; Flags: ignoreversion
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "drivers\*"; DestDir: "{app}\drivers"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PCDeck.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PCDeck.ico"; Tasks: desktopicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tray"; IconFilename: "{app}\PCDeck.ico"; Tasks: startupicon

[Registry]
; Explicitly purge any legacy HKLM / HKCU Run registry entries to prevent duplicate/triple launches
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#MyAppName}"; Flags: uninsdeletevalue deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#MyAppName}"; Flags: uninsdeletevalue deletevalue
Root: HKCU; Subkey: "Software\Classes\CLSID\{{5C2CD55C-92AD-4999-8666-912BD3E70010}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\CLSID\{{860BB310-5D01-11D0-BD3B-00A0C911CE86}\Instance\{{5C2CD55C-92AD-4999-8666-912BD3E70010}"; Flags: uninsdeletekey

[Run]
; 1. Add inbound Windows Defender Firewall rule so phone connects seamlessly over local Wi-Fi
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""PCDeck"" dir=in action=allow program=""{app}\{#MyAppExeName}"" enable=yes profile=any"; Flags: runhidden

; 2. Option to launch PCDeck right away (skipped if running silent /VERYSILENT installer)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
; 0. Forcibly close running PCDeck instance so Windows can delete all files cleanly
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden
Filename: "taskkill.exe"; Parameters: "/F /FI ""IMAGENAME eq PCDeck*"""; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""PCDeck"" /f"; Flags: runhidden

; 1. Remove Windows Defender Firewall rule
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""PCDeck"""; Flags: runhidden

; 2. Delete Task Scheduler autostart task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""PCDeck"" /f"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{autopf}\{#MyAppName}"
Type: files; Name: "{autodesktop}\{#MyAppName}.lnk"
Type: filesandordirs; Name: "{group}"
Type: files; Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\{#MyAppName}.lnk"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Refresh Windows Shell icon cache so desktop shortcuts immediately display the new authentic icon
    Exec('cmd.exe', '/c ie4uinit.exe -show', '', SW_HIDE, ewNoWait, ResultCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
  Cmd: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    // Spawn an asynchronous detached cmd to wait 2 seconds for unins000.exe to completely exit and release file locks, then delete the entire directory tree cleanly
    Cmd := '/c ping 127.0.0.1 -n 3 > nul & if exist "' + AppDir + '" rmdir /s /q "' + AppDir + '"';
    Exec('cmd.exe', Cmd, '', SW_HIDE, ewNoWait, ResultCode);
  end;
end;
