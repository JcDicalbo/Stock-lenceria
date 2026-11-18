; Instalador de Lencería. Compilar: "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" instalador.iss
; Se instala por usuario (sin pedir permisos de administrador) porque la base lenceria.db
; vive al lado del .exe y esa carpeta tiene que poder escribirse.

[Setup]
AppId={{7B3E2A41-5C8D-4F6A-9E1B-2D4C6A8F0B13}
AppName=Lencería
AppVersion=1.0
AppPublisher=Lencería
DefaultDirName={autopf}\Lenceria
DefaultGroupName=Lencería
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=instalador
OutputBaseFilename=Instalar Lenceria
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\Lenceria.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"

[Files]
Source: "dist\Lenceria.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Lencería"; Filename: "{app}\Lenceria.exe"
Name: "{autodesktop}\Lencería"; Filename: "{app}\Lenceria.exe"; Tasks: escritorio

[Run]
Filename: "{app}\Lenceria.exe"; Description: "Abrir Lencería ahora"; Flags: nowait postinstall skipifsilent

; lenceria.db no se borra al desinstalar: Inno solo quita lo que instaló, así los datos sobreviven.
