; Inno Setup Script for PCDeck Pro Windows Installer
; Designed for Microsoft Store Win32 & Standalone Distribution
; Author: Greshon Parichha

#define MyAppName "PCDeck"
#define MyAppVersion "2.7.0"
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
PrivilegesRequiredOverridesAllowed=dialog
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
Name: "webcamdriver"; Description: "Register Virtual HD Webcam DirectShow filters (For OBS, Discord, Zoom)"; GroupDescription: "Hardware Drivers:"; Flags: checkedonce

[Files]
Source: "PCDeck.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "drivers\*"; DestDir: "{app}\drivers"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "PCDeck.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "PCDeck.apk"; DestDir: "{app}"; Flags: ignoreversion
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PCDeck.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PCDeck.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; 1. Register 64-bit and 32-bit DirectShow Virtual Webcam Filters silently
Filename: "regsvr32.exe"; Parameters: "/s ""{app}\drivers\UnityCaptureFilter64.dll"""; Flags: runhidden; Tasks: webcamdriver
Filename: "regsvr32.exe"; Parameters: "/s ""{app}\drivers\UnityCaptureFilter32.dll"""; Flags: runhidden; Tasks: webcamdriver

; 2. Add inbound Windows Defender Firewall rule so phone connects seamlessly over local Wi-Fi
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""PCDeck"" dir=in action=allow program=""{app}\{#MyAppExeName}"" enable=yes profile=any"; Flags: runhidden

; 3. Option to launch PCDeck right away (skipped if running silent /VERYSILENT installer)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
; 0. Forcibly close running PCDeck instance so Windows can delete all files cleanly
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden
Filename: "taskkill.exe"; Parameters: "/F /FI ""IMAGENAME eq PCDeck*"""; Flags: runhidden

; 1. Unregister DirectShow Virtual Webcam Filters cleanly
Filename: "regsvr32.exe"; Parameters: "/u /s ""{app}\drivers\UnityCaptureFilter64.dll"""; Flags: runhidden
Filename: "regsvr32.exe"; Parameters: "/u /s ""{app}\drivers\UnityCaptureFilter32.dll"""; Flags: runhidden
Filename: "regsvr32.exe"; Parameters: "/u /s ""{autopf}\{#MyAppName}\drivers\UnityCaptureFilter64.dll"""; Flags: runhidden
Filename: "regsvr32.exe"; Parameters: "/u /s ""{autopf}\{#MyAppName}\drivers\UnityCaptureFilter32.dll"""; Flags: runhidden

; 2. Remove Windows Defender Firewall rule
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""PCDeck"""; Flags: runhidden

; 3. Delete Task Scheduler autostart task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""PCDeck"" /f"; Flags: runhidden

; 4. Uninstall ViGEmBus virtual gamepad driver silently via MSI if installed
Filename: "msiexec.exe"; Parameters: "/x ""{app}\drivers\ViGEmBus_x64.msi"" /qn /norestart"; Flags: runhidden

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
