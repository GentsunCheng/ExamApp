#!/usr/bin/env bash
set -euo pipefail

# 项目配置
APP_NAME="ExamSystem"
MAIN_SCRIPT="main.py"
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || true)
if [[ -n "${APP_VERSION:-}" ]]; then
    APP_VERSION="${APP_VERSION}"
elif [[ -n "$GIT_HASH" ]]; then
    APP_VERSION="$GIT_HASH"
else
    APP_VERSION="$(date +%s | sha256sum | cut -c1-8)"
fi
DIST_DIR="dist"
BUILD_DIR="build"

# 检测平台
UNAME_S=$(uname -s)
if [[ "$UNAME_S" == "Darwin" ]]; then
    PLATFORM="macos"
elif [[ "$UNAME_S" == "Linux" ]]; then
    PLATFORM="linux"
elif [[ "$OS" == "Windows_NT" ]] || [[ "$UNAME_S" == MINGW* ]] || [[ "$UNAME_S" == MSYS* ]]; then
    PLATFORM="windows"
else
    PLATFORM="unknown"
fi

# 检测核心数量
if [[ "$PLATFORM" == "windows" ]]; then
    JOBS=${NUMBER_OF_PROCESSORS:-1}
elif [[ "$PLATFORM" == "linux" ]]; then
    JOBS=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo || echo 1)
elif [[ "$PLATFORM" == "macos" ]]; then
    JOBS=$(sysctl -n hw.ncpu || echo 1)
else
    JOBS=1
fi

# 检测架构
ARCH=$(uname -m)

# 根据平台与可用模块添加隐性导入
EXTRA_HIDDEN_IMPORTS=$(python3 -c 'import importlib.util; mods=["winreg","ctypes"]; print(" ".join(["--hidden-import "+m for m in mods if importlib.util.find_spec(m)]))')

# PyInstaller 基础参数
PYINSTALLER_ARGS="--onedir --name ${APP_NAME} --distpath ${DIST_DIR} --workpath ${BUILD_DIR} ${EXTRA_HIDDEN_IMPORTS} --add-binary "resources/version:resources""

# 平台特定参数
if [[ "$PLATFORM" == "macos" ]]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --windowed --noconsole --add-data resources/sshpass_darwin:resources/sshpass_darwin --icon resources/logo.icns --osx-bundle-identifier top.orii.exam --output-folder-name=${APP_NAME}_${ARCH}"
elif [[ "$PLATFORM" == "windows" ]]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --windowed --noconsole --add-data resources/sshpass_win.exe:resources/sshpass_win.exe --icon resources/logo.ico"
elif [[ "$PLATFORM" == "linux" ]]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --noconsole --add-data resources/sshpass_linux:resources/sshpass_linux"
fi

# Nuitka 基础参数
NUITKA_ARGS="--output-dir=${DIST_DIR} --standalone --jobs=${JOBS} --lto=yes --output-filename=${APP_NAME} --output-folder-name=${APP_NAME} --include-data-file=resources/version=resources/version --enable-plugin=pyside6"

# Nuitka 平台特定参数
if [[ "$PLATFORM" == "macos" ]]; then
    NUITKA_ARGS="${NUITKA_ARGS} --macos-create-app-bundle --macos-signed-app-name=top.orii.exam --macos-app-name=${APP_NAME} --macos-target-arch=${ARCH} --include-data-file=resources/sshpass_darwin=resources/sshpass_darwin --macos-app-icon=resources/logo.icns"
elif [[ "$PLATFORM" == "windows" ]]; then
    NUITKA_ARGS="${NUITKA_ARGS} --windows-console-mode=disable --windows-icon-from-ico=resources/logo.ico --include-data-file=resources/sshpass_win.exe=resources/sshpass_win.exe --onefile-windows-splash-screen-image=resources/logo.ico"
elif [[ "$PLATFORM" == "linux" ]]; then
    NUITKA_ARGS="${NUITKA_ARGS} --include-data-file=resources/sshpass_linux=resources/sshpass_linux"
fi

CMD="${1:-help}"

case "$CMD" in
  install)
    echo "安装依赖包..."
    pip3 install -r requirements.txt
    ;;
  genkey)
    echo "生成密钥文件..."
    if [ -f conf/secret_key.py ]; then
      echo "密钥已存在，跳过"
    else
      if [ -f .env ]; then
        ENV_AES_B64=$(grep -E '^AES_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
        ENV_AES=$(grep -E '^AES_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
        ENV_HMAC_B64=$(grep -E '^SECRET_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
        ENV_HMAC=$(grep -E '^SECRET_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
        AK=${ENV_AES_B64:-$ENV_AES}
        SK=${ENV_HMAC_B64:-$ENV_HMAC}
        if [ -n "$AK" ] || [ -n "$SK" ]; then
          printf "AES_KEY = '%s'\n" "$AK" > conf/secret_key.py
          printf "SECRET_KEY = '%s'\n" "$SK" >> conf/secret_key.py
          echo "conf/secret_key.py 已生成"
        else
          python3 -c 'import os, base64; ak=os.urandom(32); sk=os.urandom(32); open("conf/secret_key.py","w").write("AES_KEY = " + repr(base64.b64encode(ak).decode("ascii")) + "\n" + "SECRET_KEY = " + repr(base64.b64encode(sk).decode("ascii")) + "\n"); print("secret_key.py 已生成")'
        fi
      else
        python3 -c 'import os, base64; ak=os.urandom(32); sk=os.urandom(32); open("conf/secret_key.py","w").write("AES_KEY = " + repr(base64.b64encode(ak).decode("ascii")) + "\n" + "SECRET_KEY = " + repr(base64.b64encode(sk).decode("ascii")) + "\n"); print("secret_key.py 已生成")'
      fi
    fi
    ;;
  build)
    echo "开始构建可执行文件..."
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    echo "${APP_VERSION}" > resources/version
    pyinstaller ${PYINSTALLER_ARGS} "${MAIN_SCRIPT}"
    rm resources/version
    if [[ "$PLATFORM" == "macos" ]]; then
        echo "构建完成: ${DIST_DIR}/${APP_NAME}.app"
    else
        echo "构建完成: ${DIST_DIR}/${APP_NAME}"
    fi
    ;;
  build-nuitka)
    echo "开始使用 Nuitka 构建..."
    rm -rf "${BUILD_DIR}" "${DIST_DIR}"
    echo "${APP_VERSION}" > resources/version
    python3 -m nuitka ${NUITKA_ARGS} "${MAIN_SCRIPT}"
    rm resources/version
    echo "Nuitka 构建完成"
    ;;
  run)
    if [[ "$PLATFORM" == "macos" ]]; then
        open "${DIST_DIR}/${APP_NAME}.app"
    else
        ./"${DIST_DIR}/${APP_NAME}/${APP_NAME}"
    fi
    ;;
  run-nuitka)
    if [[ "$PLATFORM" == "macos" ]]; then
        open "${DIST_DIR}/${APP_NAME}.app"
    else
        ./"${DIST_DIR}/${APP_NAME}/${APP_NAME}"
    fi
    ;;
  dmg)
    if [[ "$PLATFORM" != "macos" ]]; then
        echo "DMG 仅支持 macOS"
        exit 1
    fi
    rm -rf "${BUILD_DIR}/dmg"
    mkdir -p "${BUILD_DIR}/dmg"
    cp -R "${DIST_DIR}/${APP_NAME}.app" "${BUILD_DIR}/dmg/"
    ln -s /Applications "${BUILD_DIR}/dmg/Applications" || true
    hdiutil create -volname "${APP_NAME}" -srcfolder "${BUILD_DIR}/dmg" -ov -format UDZO "${DIST_DIR}/${APP_NAME}.dmg"
    echo "DMG 已创建: ${DIST_DIR}/${APP_NAME}.dmg"
    ;;
  dev)
    python3 "${MAIN_SCRIPT}"
    ;;
  clean)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    ;;
  deep-clean)
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" *.spec
    rm -rf ~/.exam_system/
    ;;
  check-deps)
    for pkg in PySide6 pyyaml Crypto pyarmor; do
      python3 -c "import ${pkg}" 2>/dev/null && echo "✓ ${pkg} 已安装" || echo "✗ ${pkg} 未安装"
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
    echo "安全构建完成"
    ;;
  package)
    echo "创建发布包..."
    cd "${DIST_DIR}" && tar -czf "${APP_NAME}-$(date +%Y%m%d).tar.gz" "${APP_NAME}"
    echo "发布包已创建: ${DIST_DIR}/${APP_NAME}-$(date +%Y%m%d).tar.gz"
    ;;
  test)
    echo "运行测试..."
    python3 -m pytest tests/test_*.py -v
    ;;
  *)
    echo "用法: ./build.sh [install|genkey|build|build-nuitka|build-secure|run|run-nuitka|dmg|dev|clean|deep-clean|check-deps|obfuscate|package|test]"
    exit 1
    ;;
esac
