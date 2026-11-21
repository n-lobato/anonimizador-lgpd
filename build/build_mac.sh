#!/usr/bin/env bash
# Gera o Anonimizador LGPD para Mac: "Anonimizador LGPD.app" dentro de um .dmg.
# O OCR já vem dentro do PyMuPDF; os dados de idioma vão no aplicativo.
# Uso (na raiz do projeto, com as dependências instaladas):
#   python build/baixar_tessdata.py
#   bash build/build_mac.sh
# O processador da máquina decide o pacote: Apple Silicon (arm64) ou Intel (x86_64).
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
PY="${PYTHON:-python}"
VERSAO="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/anonimizador/__init__.py)"
[ "$(uname -m)" = "arm64" ] && ARQ="apple-silicon" || ARQ="intel"
APP="dist/Anonimizador LGPD.app"

echo "1/5 Gerando o aplicativo (versão $VERSAO, $ARQ)..."
rm -rf dist
"$PY" -m PyInstaller --noconfirm --clean anonimizador.spec
[ -d "$APP" ] || { echo "ERRO: $APP não foi gerado"; exit 1; }
[ -f "$APP/Contents/Resources/tessdata/por.traineddata" ] || [ -f "$APP/Contents/Frameworks/tessdata/por.traineddata" ] \
    || { echo "ERRO: dados do OCR não entraram no aplicativo"; exit 1; }

echo "2/5 Conferindo a versão mínima do macOS..."
# a maior exigência entre as bibliotecas incluídas vale para o pacote inteiro
MINIMO=$(find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -perm -u+x \) -print0 \
    | { xargs -0 -n 1 vtool -show-build 2>/dev/null || true; } | awk '/minos/{print $2}' | sort -V | tail -1)
MINIMO="${MINIMO:-11.0}"
echo "    macOS mínimo: $MINIMO"
plutil -replace LSMinimumSystemVersion -string "$MINIMO" "$APP/Contents/Info.plist"
echo "$MINIMO" > "dist/macos-minimo-$ARQ.txt"
EXE="$(plutil -extract CFBundleExecutable raw "$APP/Contents/Info.plist")"
[ "$EXE" = "AnonimizadorLGPD" ] || { echo "ERRO: o aplicativo abre '$EXE' em vez da janela"; exit 1; }

echo "3/5 Assinando (assinatura local, sem certificado da Apple)..."
codesign --force --deep -s - "$APP"
codesign --verify --deep --strict "$APP"

echo "4/5 Montando o .dmg..."
DMG_DIR="$(mktemp -d)"
cp -R "$APP" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Aplicativos"
sed "s/{MINIMO}/$MINIMO/" build/LEIA-ME-mac.txt > "$DMG_DIR/LEIA-ME.txt"
SAIDA="AnonimizadorLGPD-mac-$ARQ.dmg"
rm -f "$SAIDA"
# nas máquinas Mac do GitHub o hdiutil às vezes falha com "Resource busy" sem motivo real
for tentativa in 1 2 3 4 5; do
    if hdiutil create -volname "Anonimizador LGPD" -srcfolder "$DMG_DIR" -ov -format UDZO "$SAIDA" >/dev/null; then
        break
    fi
    [ "$tentativa" = 5 ] && { echo "ERRO: hdiutil falhou 5 vezes"; exit 1; }
    echo "    hdiutil falhou (tentativa $tentativa); nova tentativa em 15 s..."
    sleep 15
done
rm -rf "$DMG_DIR"

echo "5/5 Pronto: $SAIDA ($(du -h "$SAIDA" | cut -f1))"
