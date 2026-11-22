#!/usr/bin/env bash
# Gera o Anonimizador LGPD para Linux de 64 bits (x86-64):
#   - AnonimizadorLGPD-linux-amd64.deb: Debian 12 ou mais novo, Ubuntu e derivados
#   - AnonimizadorLGPD-linux-x64.tar.gz: outras distribuições, instala só para o usuário
# O OCR já vem dentro do PyMuPDF; os dados de idioma vão no pacote.
# Gere numa distribuição antiga (o GitHub usa Ubuntu 22.04) para o pacote rodar
# também em sistemas mais velhos.
# Uso (na raiz do projeto, com as dependências instaladas):
#   python build/baixar_tessdata.py
#   bash build/build_linux.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
PY="${PYTHON:-python}"
VERSAO="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/anonimizador/__init__.py)"
NOME="anonimizador-lgpd"

echo "1/4 Gerando os executáveis (versão $VERSAO)..."
rm -rf dist
"$PY" -m PyInstaller --noconfirm --clean anonimizador.spec
APP="dist/AnonimizadorLGPD"
[ -f "$APP/_internal/tessdata/por.traineddata" ] || { echo "ERRO: dados do OCR não entraram no pacote"; exit 1; }
cp README.md LICENSE "$APP/"
"$PY" build/coletar_licencas.py "$APP"
cp build/LEIA-ME-linux.txt "$APP/LEIA-ME.txt"
cp assets/icone.png "$APP/$NOME.png"

echo "2/4 Pacote .deb..."
DEB="$(mktemp -d)"
mkdir -p "$DEB/DEBIAN" "$DEB/opt" "$DEB/usr/bin" "$DEB/usr/share/applications" \
         "$DEB/usr/share/icons/hicolor/256x256/apps" "$DEB/usr/share/doc/$NOME"
cp -R "$APP" "$DEB/opt/$NOME"
ln -s "/opt/$NOME/AnonimizadorLGPD" "$DEB/usr/bin/$NOME"
ln -s "/opt/$NOME/anonimizador-cli" "$DEB/usr/bin/anonimizador-cli"
cp assets/icone.png "$DEB/usr/share/icons/hicolor/256x256/apps/$NOME.png"
cat > "$DEB/usr/share/applications/$NOME.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Anonimizador LGPD
Comment=Encontra e tarja dados pessoais em documentos, no próprio computador
Exec=$NOME %F
Icon=$NOME
Terminal=false
Categories=Office;Utility;
Keywords=lgpd;anonimizar;tarja;cpf;pdf;docx;ocr;
DESK
cat > "$DEB/usr/share/doc/$NOME/copyright" <<COPY
Anonimizador LGPD
Copyright (C) 2026 n-lobato
Licença: GNU GPL v3. Texto completo em /opt/$NOME/LICENSE.
Componentes de terceiros e suas licenças: /opt/$NOME/THIRD-PARTY-NOTICES.md e /opt/$NOME/LICENCAS.
Código-fonte: https://github.com/n-lobato/anonimizador-lgpd
COPY
TAMANHO=$(du -sk "$DEB/opt" | cut -f1)
# bibliotecas gráficas que o Qt usa e que não vão dentro do pacote
cat > "$DEB/DEBIAN/control" <<CTRL
Package: $NOME
Version: $VERSAO
Section: utils
Priority: optional
Architecture: amd64
Maintainer: n-lobato <n-lobato@users.noreply.github.com>
Homepage: https://github.com/n-lobato/anonimizador-lgpd
Installed-Size: $TAMANHO
Depends: libc6 (>= 2.35), libegl1, libgl1, libfontconfig1, libfreetype6, libdbus-1-3, libglib2.0-0, libx11-xcb1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xfixes0, libxcb-xinerama0, libxcb-xkb1, libwayland-client0, libwayland-cursor0, libwayland-egl1
Description: Anonimiza dados pessoais em documentos, sem internet
 Encontra e substitui nomes, CPF, RG, endereços e outros dados pessoais em
 petições, certidões, atas e transcrições (Word, PDF, imagens, texto e Excel).
 Grava uma cópia no mesmo formato do original, com tarja definitiva no PDF,
 OCR para documentos digitalizados e revisão antes de salvar.
CTRL
chmod -R u=rwX,go=rX "$DEB"
chmod 755 "$DEB/opt/$NOME/AnonimizadorLGPD" "$DEB/opt/$NOME/anonimizador-cli"
rm -f AnonimizadorLGPD-linux-amd64.deb
dpkg-deb --root-owner-group --build "$DEB" AnonimizadorLGPD-linux-amd64.deb >/dev/null
rm -rf "$DEB"

echo "3/4 Pacote .tar.gz..."
TAR="$(mktemp -d)"
PASTA="AnonimizadorLGPD-linux-x64"
mkdir -p "$TAR/$PASTA"
cp -R "$APP" "$TAR/$PASTA/$NOME"
cp build/linux/instalar.sh build/linux/desinstalar.sh build/LEIA-ME-linux.txt "$TAR/$PASTA/"
mv "$TAR/$PASTA/LEIA-ME-linux.txt" "$TAR/$PASTA/LEIA-ME.txt"
chmod +x "$TAR/$PASTA/instalar.sh" "$TAR/$PASTA/desinstalar.sh"
rm -f "$PASTA.tar.gz"
tar -C "$TAR" -czf "$PASTA.tar.gz" "$PASTA"
rm -rf "$TAR"

echo "4/4 Pronto:"
ls -lh AnonimizadorLGPD-linux-amd64.deb "$PASTA.tar.gz"
