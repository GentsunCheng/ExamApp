# Makefile for Exam System

# 项目配置
APP_NAME = ExamSystem
PYTHON_VERSION = 3.9+
MAIN_SCRIPT = main.py
DIST_DIR = dist
BUILD_DIR = build
JOBS ?= 1

# 检测平台
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    PLATFORM := macos
else ifeq ($(UNAME_S),Linux)
    PLATFORM := linux
else ifeq ($(UNAME_S),Windows_NT)
    PLATFORM := windows
else ifneq (,$(findstring MINGW,$(UNAME_S)))
    PLATFORM := windows
else ifneq (,$(findstring MSYS,$(UNAME_S)))
    PLATFORM := windows
else
    PLATFORM := unknown
endif

# 检测核心数量

ifeq ($(OS),Windows_NT)
    # Windows 平台
    JOBS := $(shell echo %NUMBER_OF_PROCESSORS%)
else ifeq ($(UNAME_S),Linux)
    # Linux 平台
    JOBS := $(shell nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo)
else ifeq ($(UNAME_S),Darwin)
    # macOS 平台
    JOBS := $(shell sysctl -n hw.ncpu)
endif

# 检测架构
ARCH ?= $(shell uname -m)

# PyInstaller 配置
PYINSTALLER = pyinstaller

PYINSTALLER_COMMON_ARGS = \
    --onedir \
    --name $(APP_NAME) \
    --distpath $(DIST_DIR) \
    --workpath $(BUILD_DIR) \

PYINSTALLER_MACOS_ARGS = \
    --windowed \
    --noconsole \
	--add-data "resources/sshpass_darwin:resources/sshpass_darwin" \
    --icon resources/logo.icns \
    --osx-bundle-identifier top.orii.exam \
	--output-folder-name=$(APP_NAME)_$(ARCH)

PYINSTALLER_WINDOWS_ARGS = \
    --windowed \
    --noconsole \
	--add-data "resources/sshpass_win.exe:resources/sshpass_win.exe" \
    --icon resources/logo.ico

PYINSTALLER_LINUX_ARGS = \
    --noconsole \
	--add-data "resources/sshpass_linux:resources/sshpass_linux"

ifeq ($(PLATFORM),macos)
    PYINSTALLER_ARGS = $(PYINSTALLER_COMMON_ARGS) $(PYINSTALLER_MACOS_ARGS)
else ifeq ($(PLATFORM),windows)
    PYINSTALLER_ARGS = $(PYINSTALLER_COMMON_ARGS) $(PYINSTALLER_WINDOWS_ARGS)
else ifeq ($(PLATFORM),linux)
    PYINSTALLER_ARGS = $(PYINSTALLER_COMMON_ARGS) $(PYINSTALLER_LINUX_ARGS)
else
    $(error Unsupported platform: $(UNAME_S))
endif

# nuitka 配置
NUITKA = nuitka

NUITKA_COMPILE_ARGS = \
    --output-dir=$(DIST_DIR) \
	--standalone \
	--jobs=$(JOBS) \
	--lto=yes \
	--output-filename=$(APP_NAME) \
	--output-folder-name=$(APP_NAME) \
	--enable-plugin=pyside6

NUITKA_MACOS_ARGS = \
	--macos-create-app-bundle \
    --macos-signed-app-name=top.orii.exam \
	--macos-app-name=$(APP_NAME) \
	--macos-target-arch=$(ARCH) \
	--include-data-file=resources/sshpass_darwin=resources/sshpass_darwin \
    --macos-app-icon=resources/logo.icns

NUITKA_WINDOWS_ARGS = \
    --windows-console-mode=disable \
	--windows-icon-from-ico=resources/logo.ico \
	--include-data-file=resources/sshpass_win.exe=resources/sshpass_win.exe \
	--onefile-windows-splash-screen-image=resources/logo.ico

NUITKA_LINUX_ARGS = \
	--include-data-file=resources/sshpass_linux=resources/sshpass_linux \
    --linux-icon=resources/logo.png

ifeq ($(PLATFORM),macos)
    NUITKA_ARGS = $(NUITKA_COMPILE_ARGS) $(NUITKA_MACOS_ARGS)
else ifeq ($(PLATFORM),windows)
    NUITKA_ARGS = $(NUITKA_COMPILE_ARGS) $(NUITKA_WINDOWS_ARGS)
else ifeq ($(PLATFORM),linux)
    NUITKA_ARGS = $(NUITKA_COMPILE_ARGS) $(NUITKA_LINUX_ARGS)
else
    $(error Unsupported platform: $(UNAME_S))
endif

# 根据平台与可用模块添加隐性导入（动态 importlib 使用的模块）
EXTRA_HIDDEN_IMPORTS := $(shell python -c 'import importlib, sys; mods=["winreg","ctypes"]; print(" ".join(["--hidden-import "+m for m in mods if importlib.util.find_spec(m)]))')
PYINSTALLER_ARGS += $(EXTRA_HIDDEN_IMPORTS)

# 依赖的Python包
REQUIRED_PACKAGES = \
    PySide6 \
    pyyaml \
    pycryptodome

# 默认目标
.PHONY: all
all: install build

# 安装依赖
.PHONY: install
install:
	@echo "安装依赖包..."
	pip3 install -r requirements.txt
	@echo "安装完成!"

# 清理构建文件
.PHONY: clean
clean:
	@echo "清理构建文件..."
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.spec
	@echo "清理完成!"

# 清理所有文件（包括数据库）
.PHONY: deep-clean
deep-clean: clean
	@echo "清理所有文件..."
	rm -rf ~/.exam_system/
	@echo "深度清理完成!"

# 构建可执行文件
.PHONY: build
build: clean
	@echo "开始构建可执行文件..."
	$(PYINSTALLER) $(PYINSTALLER_ARGS) $(MAIN_SCRIPT)
	@echo "构建完成! 可执行文件位于: $(DIST_DIR)/$(APP_NAME).app"

# 使用nuitka构建
.PHONY: build-nuitka
build-nuitka: clean
	@echo "开始使用nuitka构建..."
	$(NUITKA) $(NUITKA_ARGS) $(MAIN_SCRIPT)
	@echo "nuitka构建完成! 可执行文件位于: $(DIST_DIR)/$(APP_NAME)"

# 构建并运行
.PHONY: run
run: build
	@echo "运行可执行文件..."
	open "$(DIST_DIR)/$(APP_NAME).app"

# 使用nuitka运行
.PHONY: run-nuitka
run-nuitka: build-nuitka
	@echo "运行nuitka可执行文件..."
	open "$(DIST_DIR)/$(APP_NAME)"

# 生成 DMG 安装镜像
.PHONY: dmg
dmg: build
	@echo "创建DMG镜像..."
	rm -rf $(BUILD_DIR)/dmg
	mkdir -p $(BUILD_DIR)/dmg
	cp -R "$(DIST_DIR)/$(APP_NAME).app" "$(BUILD_DIR)/dmg/"
	ln -s /Applications "$(BUILD_DIR)/dmg/Applications"
	hdiutil create -volname "$(APP_NAME)" -srcfolder "$(BUILD_DIR)/dmg" -ov -format UDZO "$(DIST_DIR)/$(APP_NAME).dmg"
	@echo "DMG已创建: $(DIST_DIR)/$(APP_NAME).dmg"

# 使用 PyArmor 导出混淆代码
.PHONY: obfuscate
obfuscate:
	@echo "使用 PyArmor 导出混淆代码..."
	@mkdir -p obf
	@pyarmor gen -O obf -r . || pyarmor obfuscate -r -O obf .
	@echo "混淆代码已导出到: obf/"

# 使用 PyArmor 打包（包含代码混淆）
.PHONY: build-secure
build-secure: clean
	@echo "使用 PyArmor 打包（包含代码混淆）..."
	@pyarmor pack -e "$(PYINSTALLER_ARGS)" "$(MAIN_SCRIPT)"
	@echo "安全构建完成"

# 开发模式运行
.PHONY: dev
dev:
	@echo "开发模式运行..."
	python $(MAIN_SCRIPT)

# 打包发布
.PHONY: package
package: build
	@echo "创建发布包..."
	cd $(DIST_DIR) && tar -czf $(APP_NAME)-$(shell date +%Y%m%d).tar.gz $(APP_NAME)
	@echo "发布包已创建: $(DIST_DIR)/$(APP_NAME)-$(shell date +%Y%m%d).tar.gz"

# 使用nuitka打包发布
.PHONY: package-nuitka
package-nuitka: build-nuitka
	@echo "创建nuitka发布包..."
	cd $(DIST_DIR) && tar -czf $(APP_NAME)-$(shell date +%Y%m%d).tar.gz $(APP_NAME)
	@echo "nuitka发布包已创建: $(DIST_DIR)/$(APP_NAME)-$(shell date +%Y%m%d).tar.gz"

# 检查依赖
.PHONY: check-deps
check-deps:
	@echo "检查依赖包..."
	@for pkg in $(REQUIRED_PACKAGES); do \
		python -c "import $$pkg" 2>/dev/null && echo "✓ $$pkg 已安装" || echo "✗ $$pkg 未安装"; \
	done

# 测试
.PHONY: test
test:
	@echo "运行测试..."
	python -m pytest test_*.py -v

# 帮助
.PHONY: help
help:
	@echo "Exam System Makefile"
	@echo "可用命令:"
	@echo "  make install     - 安装依赖包"
	@echo "  make build         - 构建可执行文件"
	@echo "  make build-nuitka - 使用nuitka构建可执行文件"
	@echo "  make run          - 构建并运行"
	@echo "  make run-nuitka   - 使用nuitka运行"
	@echo "  make dmg          - 生成DMG安装镜像"
	@echo "  make dev          - 开发模式运行"
	@echo "  make clean        - 清理构建文件"
	@echo "  make package      - 创建发布包"
	@echo "  make package-nuitka - 使用nuitka创建发布包"
	@echo "  make check-deps  - 检查依赖包"
	@echo "  make test         - 运行测试"
	@echo "  make help          - 显示此帮助信息"
	@echo "  make obfuscate    - 使用 PyArmor 导出混淆代码到 obf/"
	@echo "  make build-secure - 使用 PyArmor 打包（包含代码混淆）"
# 生成密钥文件
.PHONY: genkey
genkey:
	@echo "生成密钥文件..."
	@if [ -f conf/serect_key.py ]; then \
		echo "密钥已存在，跳过"; \
	else \
		if [ -f .env ]; then \
			ENV_AES_B64=$$(grep -E '^AES_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			ENV_AES=$$(grep -E '^AES_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			ENV_HMAC_B64=$$(grep -E '^SERECT_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			ENV_HMAC=$$(grep -E '^SERECT_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			AK=$${ENV_AES_B64:-$$ENV_AES}; \
			SK=$${ENV_HMAC_B64:-$$ENV_HMAC}; \
			if [ -n "$$AK" ] || [ -n "$$SK" ]; then \
				printf "AES_KEY = '%s'\n" "$$AK" > conf/serect_key.py; \
				printf "SERECT_KEY = '%s'\n" "$$SK" >> conf/serect_key.py; \
				echo "conf/serect_key.py 已生成"; \
			else \
				python3 -c "import os, base64; ak=os.urandom(32); sk=os.urandom(32); open('conf/serect_key.py','w').write('AES_KEY = ' + repr(base64.b64encode(ak).decode('ascii')) + '\n' + 'SERECT_KEY = ' + repr(base64.b64encode(sk).decode('ascii')) + '\n'); print('serect_key.py 已生成')"; \
			fi; \
		else \
			python3 -c "import os, base64; ak=os.urandom(32); sk=os.urandom(32); open('conf/serect_key.py','w').write('AES_KEY = ' + repr(base64.b64encode(ak).decode('ascii')) + '\n' + 'SERECT_KEY = ' + repr(base64.b64encode(sk).decode('ascii')) + '\n'); print('serect_key.py 已生成')"; \
		fi; \
	fi
