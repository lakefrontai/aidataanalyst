; NSIS installer script for AI Data Analyst (Windows)
; Produces: dist/AIDataAnalyst-Setup.exe

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "AI Data Analyst"
OutFile "dist\AIDataAnalyst-Setup.exe"
InstallDir "$PROGRAMFILES64\AIDataAnalyst"
InstallDirRegKey HKLM "Software\AIDataAnalyst" "Install_Dir"
RequestExecutionLevel admin

; MUI settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE "AI Data Analyst Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will install AI Data Analyst on your computer.$\n$\nClick Next to continue."

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Installer
Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\AIDataAnalyst\*.*"

  ; Start menu shortcut
  CreateDirectory "$SMPROGRAMS\AI Data Analyst"
  CreateShortcut "$SMPROGRAMS\AI Data Analyst\AI Data Analyst.lnk" \
    "$INSTDIR\AIDataAnalyst.exe" "" "$INSTDIR\AIDataAnalyst.exe"
  CreateShortcut "$DESKTOP\AI Data Analyst.lnk" \
    "$INSTDIR\AIDataAnalyst.exe" "" "$INSTDIR\AIDataAnalyst.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add/Remove Programs entry
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst" \
    "DisplayName" "AI Data Analyst"
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst" \
    "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst" \
    "DisplayVersion" "1.0.0"
  WriteRegStr HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst" \
    "Publisher" "Lakefront AI"

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst" \
    "EstimatedSize" "$0"
SectionEnd

; Uninstaller
Section "Uninstall"
  Delete "$SMPROGRAMS\AI Data Analyst\AI Data Analyst.lnk"
  Delete "$DESKTOP\AI Data Analyst.lnk"
  RMDir "$SMPROGRAMS\AI Data Analyst"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\AIDataAnalyst"
SectionEnd
