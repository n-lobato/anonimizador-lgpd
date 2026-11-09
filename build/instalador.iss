; Instalador do Anonimizador LGPD para Windows (Inno Setup 6).
; Instala só para o usuário atual, sem pedir senha de administrador,
; em %LOCALAPPDATA%\Programs\Anonimizador LGPD, e aparece em "Aplicativos instalados".
;
; Uso: iscc /DVersao=1.2.0 /DOrigem="C:\caminho\dist\AnonimizadorLGPD" build\instalador.iss
; (Origem é a pasta gerada pelo PyInstaller, a mesma que vai no .zip portátil.)

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Origem
  #error Informe /DOrigem com a pasta do programa gerada pelo PyInstaller
#endif

[Setup]
; não troque o AppId: é ele que liga as versões novas à instalação anterior
AppId={{B3E7A1D4-58C2-4F0E-9D61-2A7C4E8F1B95}
AppName=Anonimizador LGPD
AppVersion={#Versao}
AppVerName=Anonimizador LGPD {#Versao}
AppPublisher=n-lobato
AppPublisherURL=https://github.com/n-lobato/anonimizador-lgpd
AppSupportURL=https://github.com/n-lobato/anonimizador-lgpd/issues
AppUpdatesURL=https://github.com/n-lobato/anonimizador-lgpd/releases
VersionInfoVersion={#Versao}
DefaultDirName={autopf}\Anonimizador LGPD
DefaultGroupName=Anonimizador LGPD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\AnonimizadorLGPD.exe
UninstallDisplayName=Anonimizador LGPD
OutputDir=..\dist
OutputBaseFilename=AnonimizadorLGPD-windows-instalador
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; numa atualização, apaga a pasta interna antiga para não sobrar biblioteca de outra versão
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Anonimizador LGPD"; Filename: "{app}\AnonimizadorLGPD.exe"
Name: "{autodesktop}\Anonimizador LGPD"; Filename: "{app}\AnonimizadorLGPD.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AnonimizadorLGPD.exe"; Description: "{cm:LaunchProgram,Anonimizador LGPD}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; configurações do programa, que incluem as listas de termos próprios ("sempre"/"nunca")
Type: filesandordirs; Name: "{userappdata}\AnonimizadorLGPD"
; atalho do menu "Enviar para", se o usuário tiver criado pela janela
Type: files; Name: "{userappdata}\Microsoft\Windows\SendTo\Anonimizador LGPD.lnk"
