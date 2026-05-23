; installer.iss — Inno Setup script.
; 1) Build dist\ScreenLoupe.exe first (see build.ps1).
; 2) Install Inno Setup (https://jrsoftware.org/isdl.php), open this file,
;    and click Compile. Output: Output\ScreenLoupe-Setup.exe
;
; This installer:
;   * copies ScreenLoupe.exe into Program Files,
;   * adds a Start Menu entry "ScreenLoupe Settings" (so searching the Start
;     menu for "screenloupe" opens the settings panel),
;   * shows a setup checkbox "Run ScreenLoupe at Windows startup" (checked by
;     default) that writes the per-user Run registry key,
;   * offers to launch the magnifier right after install.

#define AppName "ScreenLoupe"
#define AppVersion "0.1.0"
#define ExeName "ScreenLoupe.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=ScreenLoupe-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
; Listed without the "unchecked" flag => CHECKED by default.
Name: "startup"; Description: "Run {#AppName} at Windows startup"

[Icons]
; Start Menu search hits this -> opens the settings GUI.
Name: "{group}\{#AppName} Settings"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Registry]
; Only written when the "startup" task is selected.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#ExeName}"" --background"; \
    Flags: uninsdeletevalue; Tasks: startup

[Run]
; Start the background magnifier now (no window). Optional, user can untick.
Filename: "{app}\{#ExeName}"; Parameters: "--background"; Description: "Start {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Best-effort: nothing to clean beyond the registry value handled above.
