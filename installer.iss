; installer.iss — instalador per-user do Sopro (docs/09 §5).
; Compilar com: iscc /DVersion=0.1.0 installer.iss

#ifndef Version
#define Version "0.0.0"
#endif

[Setup]
AppId={{8F3C5A7E-1D2B-4C6A-9E10-5B2A7C4D8F31}
AppName=Sopro
AppVersion={#Version}
AppPublisher=Mantenedores do Sopro
VersionInfoVersion={#Version}
DefaultDirName={localappdata}\Programs\Sopro
DefaultGroupName=Sopro
PrivilegesRequired=lowest
OutputBaseFilename=Sopro-Setup-{#Version}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\Sopro.exe
; Dados/modelos ficam em {localappdata}\Sopro e NÃO são removidos na desinstalação.

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "dist\Sopro\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Sopro"; Filename: "{app}\Sopro.exe"
Name: "{userdesktop}\Sopro"; Filename: "{app}\Sopro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Sopro.exe"; Description: "Abrir o Sopro"; Flags: nowait postinstall skipifsilent
