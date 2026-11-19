Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!ifndef APP_VERSION
  !define APP_VERSION "0.7.2"
!endif
!ifndef SOURCE_DIR
  !define SOURCE_DIR "..\dist\BIQMapa"
!endif
!ifndef OUTPUT_FILE
  !define OUTPUT_FILE "..\release\BIQMapa-Setup-${APP_VERSION}.exe"
!endif
Name "BIQMapa"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\BIQMapa"
InstallDirRegKey HKCU "Software\BIQMapa" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "BIQMapa · Mapeamento Urbano"
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1046 "ProductName" "BIQMapa"
VIAddVersionKey /LANG=1046 "CompanyName" "Lucas Cézar de Oliveira"
VIAddVersionKey /LANG=1046 "FileDescription" "Instalador do BIQMapa"
VIAddVersionKey /LANG=1046 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1046 "LegalCopyright" "Lucas Cézar de Oliveira"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\BIQMapa.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Abrir o BIQMapa"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Esta versão requer Windows de 64 bits."
    Abort
  ${EndIf}
FunctionEnd

Section "BIQMapa" SEC_MAIN
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  ClearErrors
  FileOpen $0 "$INSTDIR\BIQMapa.exe" a
  ${IfNot} ${Errors}
    FileClose $0
  ${Else}
    IfFileExists "$INSTDIR\BIQMapa.exe" 0 +3
    MessageBox MB_ICONSTOP "Feche o BIQMapa antes de atualizar."
    Abort
  ${EndIf}
  File /r "${SOURCE_DIR}\*"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  CreateDirectory "$SMPROGRAMS\BIQMapa"
  CreateShortcut "$SMPROGRAMS\BIQMapa\BIQMapa.lnk" "$INSTDIR\BIQMapa.exe"
  CreateShortcut "$SMPROGRAMS\BIQMapa\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
  CreateShortcut "$DESKTOP\BIQMapa.lnk" "$INSTDIR\BIQMapa.exe"
  WriteRegStr HKCU "Software\BIQMapa" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "DisplayName" "BIQMapa"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "Publisher" "Lucas Cézar de Oliveira"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "DisplayIcon" "$INSTDIR\BIQMapa.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "UninstallString" '$"$INSTDIR\Desinstalar.exe$"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\BIQMapa.lnk"
  RMDir /r "$SMPROGRAMS\BIQMapa"
  Delete "$INSTDIR\BIQMapa.exe"
  Delete "$INSTDIR\Desinstalar.exe"
  Delete "$INSTDIR\THIRD_PARTY.md"
  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\licencas"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\BIQMapa"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BIQMapa"
SectionEnd
