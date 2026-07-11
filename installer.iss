; Inno Setup script — สร้าง installer wizard สำหรับ Claude Usage Tray
; ต้องมี Inno Setup (https://jrsoftware.org/isdl.php) แล้วคอมไพล์ด้วย:
;     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; ผลลัพธ์: dist_installer\ClaudeUsageTray-Setup.exe

#define MyAppName "Claude Usage Tray"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "TopTier"
#define MyAppExeName "ClaudeUsageTray.exe"

[Setup]
AppId={{7B2C9E14-8A3F-4D2B-9C11-CLAUDEUSAGE01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Claude Usage Tray
DefaultGroupName=Claude Usage Tray
DisableProgramGroupPage=yes
; ติดตั้งระดับผู้ใช้ ไม่ต้องสิทธิ์ admin
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=ClaudeUsageTray-Setup
SetupIconFile=assets\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "thai"; MessagesFile: "compiler:Default.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบนหน้าจอ (Desktop)"; GroupDescription: "ทางลัด:"
Name: "startup"; Description: "เริ่มโปรแกรมอัตโนมัติเมื่อเปิดเครื่อง (แนะนำ)"; GroupDescription: "การเริ่มทำงาน:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\Claude Usage Tray"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\ถอนการติดตั้ง Claude Usage Tray"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Claude Usage Tray"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; autostart ผ่าน HKCU Run key (ตรงกับที่ตัวแอปจัดการเอง) — สร้างเมื่อเลือก task
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "ClaudeUsageTray"; ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "เปิด Claude Usage Tray เดี๋ยวนี้"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; ปิดโปรแกรมก่อนถอนติดตั้ง (กันไฟล์ถูกล็อก)
Filename: "{cmd}"; Parameters: "/c taskkill /IM {#MyAppExeName} /F"; Flags: runhidden; RunOnceId: "KillApp"
