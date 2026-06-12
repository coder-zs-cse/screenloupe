; ============================================================================
; ScreenLoupe — Inno Setup 6 installer script (Phase 7 deliverable)
; Build: ISCC installer\screenloupe.iss   (after PyInstaller --onedir build)
; Expects app files at: dist\ScreenLoupe\  (relative to repo root)
; ============================================================================

#define MyAppName "ScreenLoupe"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Zubie"
#define MyAppURL "https://github.com/<owner>/screenloupe"
#define MyAppExeName "ScreenLoupe.exe"

[Setup]
AppId={{B7E6C1A2-5F4D-4C9B-9D31-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
; --- Per-user install: no UAC prompt, lands in %LOCALAPPDATA%\Programs ---
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
; --- Hard floor: WDA_EXCLUDEFROMCAPTURE needs Win10 2004 (build 19041) ---
MinVersion=10.0.19041
OutputDir=..\dist
OutputBaseFilename=ScreenLoupe-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
WizardImageFile=..\assets\wizard-banner.bmp
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; Friendlier block message than the stock one when MinVersion fails
WinVersionTooLowError=ScreenLoupe needs Windows 10 version 2004 (build 19041) or newer — its overlay technology (capture exclusion) isn't available on older builds.

[Tasks]
; Product spec § 7: Start Menu ☑, run at startup ☑, desktop icon ☐
Name: "startmenu";  Description: "Create a &Start Menu shortcut";            GroupDescription: "Shortcuts:"
Name: "desktopicon"; Description: "Create a &Desktop shortcut";              GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startup";    Description: "&Run ScreenLoupe when Windows starts";     GroupDescription: "Startup:"

[Files]
Source: "..\dist\ScreenLoupe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{userdesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; HKCU Run key — same value the in-app toggle manages (platformwin/startup.py).
; uninsdeletevalue: uninstaller removes it even if the user later toggled it on in-app.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppName}"; \
    ValueData: """{app}\{#MyAppExeName}"" --minimized"; \
    Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Make sure the tray instance is closed before files are removed
Filename: "taskkill"; Parameters: "/im {#MyAppExeName} /f"; Flags: runhidden; RunOnceId: "KillTray"

[Code]
// Product spec § 7: on uninstall, ask whether to delete %APPDATA%\ScreenLoupe (config + logs)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\{#MyAppName}');
    if DirExists(DataDir) then
      if MsgBox('Also delete your ScreenLoupe settings and logs?' #13#10 + DataDir,
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
