#!/usr/bin/env bash
# Instala o Anonimizador LGPD só para o seu usuário (sem sudo), em ~/.local.
# Depois disso ele aparece no menu de aplicativos.
set -euo pipefail
NOME="anonimizador-lgpd"
ORIGEM="$(cd "$(dirname "$0")" && pwd)/$NOME"
DESTINO="$HOME/.local/share/$NOME"
[ -x "$ORIGEM/AnonimizadorLGPD" ] || { echo "Rode este script de dentro da pasta extraída."; exit 1; }

rm -rf "$DESTINO"
mkdir -p "$DESTINO" "$HOME/.local/bin" "$HOME/.local/share/applications" \
         "$HOME/.local/share/icons/hicolor/256x256/apps"
cp -R "$ORIGEM/." "$DESTINO/"
ln -sf "$DESTINO/AnonimizadorLGPD" "$HOME/.local/bin/$NOME"
ln -sf "$DESTINO/anonimizador-cli" "$HOME/.local/bin/anonimizador-cli"
cp "$DESTINO/$NOME.png" "$HOME/.local/share/icons/hicolor/256x256/apps/$NOME.png"
cat > "$HOME/.local/share/applications/$NOME.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Anonimizador LGPD
Comment=Encontra e tarja dados pessoais em documentos, no próprio computador
Exec="$DESTINO/AnonimizadorLGPD" %F
Icon=$NOME
Terminal=false
Categories=Office;Utility;
DESK
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Anonimizador LGPD instalado. Procure por ele no menu de aplicativos."
