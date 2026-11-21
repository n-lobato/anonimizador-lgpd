#!/usr/bin/env bash
# Remove o Anonimizador LGPD instalado pelo instalar.sh, inclusive as configurações
# e as listas de termos próprios. Os documentos anonimizados não são apagados.
set -euo pipefail
NOME="anonimizador-lgpd"
rm -rf "$HOME/.local/share/$NOME" "${XDG_CONFIG_HOME:-$HOME/.config}/$NOME"
rm -f "$HOME/.local/bin/$NOME" "$HOME/.local/bin/anonimizador-cli" \
      "$HOME/.local/share/applications/$NOME.desktop" \
      "$HOME/.local/share/icons/hicolor/256x256/apps/$NOME.png"
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Anonimizador LGPD removido."
