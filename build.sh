#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ExamSystem"
MAIN_SCRIPT="main.py"
DIST_DIR="dist"
BUILD_DIR="build"
PYINSTALLER_ARGS="--onedir --noconsole --windowed --name ${APP_NAME} --distpath ${DIST_DIR} --workpath ${BUILD_DIR} --add-data resources:resources --icon resources/logo.icns --osx-bundle-identifier top.orii.exam"

CMD="${1:-help}"

case "$CMD" in
  install)
    pip3 install -r requirements.txt
    ;;
  genkey)
    if [ -f conf/serect_key.py ]; then
      echo "密钥已存在，跳过"
    else
      if [ -f .env ]; then
        ENV_AES_B64=$(grep -E '^AES_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
        ENV_AES=$(grep -E '^AES_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
        ENV_HMAC_B64=$(grep -E '^SERECT_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
        ENV_HMAC=$(grep -E '^SERECT_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
        AK=${ENV_AES_B64:-$ENV_AES}
        SK=${ENV_HMAC_B64:-$ENV_HMAC}
        if [ -n "$AK" ] || [ -n "$SK" ]; then
          printf "AES_KEY = '%s'\n" "$AK" > conf/serect_key.py
          printf "SERECT_KEY = '%s'\n" "$SK" >> conf/serect_key.py
          echo "conf/serect_key.py 已生成"
        else
          python3 -c 'import os, base64; ak=os.urandom(32); sk=os.urandom(32); open("conf/serect_key.py","w").write("AES_KEY = " + repr(base64.b64encode(ak).decode("ascii")) + "\n" + "SERECT_KEY = " + repr(base64.b64encode(sk).decode("ascii")) + "\n"); print("serect_key.py 已生成")'
        fi
      else
        python3 -c 'import os, base64; ak=os.urandom(32); sk=os.urandom(32); open("conf/serect_key.py","w").write("AES_KEY = " + repr(base64.b64encode(ak).decode("ascii")) + "\n" + "SERECT_KEY = " + repr(base64.b64encode(sk).decode("ascii")) + "\n"); print("serect_key.py 已生成")'
      fi
    fi
    ;;
  build)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    pyinstaller ${PYINSTALLER_ARGS} "${MAIN_SCRIPT}"
    echo "构建完成: ${DIST_DIR}/${APP_NAME}.app"
    ;;
  run)
    open "${DIST_DIR}/${APP_NAME}.app"
    ;;
  dmg)
    rm -rf "${BUILD_DIR}/dmg"
    mkdir -p "${BUILD_DIR}/dmg"
    cp -R "${DIST_DIR}/${APP_NAME}.app" "${BUILD_DIR}/dmg/"
    ln -s /Applications "${BUILD_DIR}/dmg/Applications" || true
    hdiutil create -volname "${APP_NAME}" -srcfolder "${BUILD_DIR}/dmg" -ov -format UDZO "${DIST_DIR}/${APP_NAME}.dmg"
    echo "DMG 已创建: ${DIST_DIR}/${APP_NAME}.dmg"
    ;;
  dev)
    python "${MAIN_SCRIPT}"
    ;;
  clean)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    ;;
  deep-clean)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    rm -rf ~/.exam_system/
    ;;
  check-deps)
    for pkg in PySide6 pyyaml pycryptodome pyarmor; do
      python -c "import ${pkg}" 2>/dev/null && echo "✓ ${pkg} 已安装" || echo "✗ ${pkg} 未安装"
    done
    ;;
  obfuscate)
    echo "使用 PyArmor 导出混淆代码..."
    mkdir -p obf
    pyarmor gen -O obf -r . || pyarmor obfuscate -r -O obf .
    echo "混淆代码已导出到: obf/"
    ;;
  build-secure)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    echo "使用 PyArmor 打包（包含代码混淆）..."
    pyarmor pack -e "${PYINSTALLER_ARGS}" "${MAIN_SCRIPT}"
    echo "安全构建完成: ${DIST_DIR}/${APP_NAME}.app"
    ;;
  *)
    echo "用法: ./build.sh [install|genkey|build|build-secure|run|dmg|dev|clean|deep-clean|check-deps|obfuscate]"
    exit 1
    ;;
esac
