# Makefile for Exam System

# 项目配置
APP_NAME = ExamSystem
PYTHON_VERSION = 3.9+
MAIN_SCRIPT = main.py
DIST_DIR = dist
BUILD_DIR = build

# PyInstaller 配置
PYINSTALLER = pyinstaller
PYINSTALLER_ARGS = --onedir --noconsole --windowed --name $(APP_NAME) --distpath $(DIST_DIR) \
 --workpath $(BUILD_DIR) --add-data "resources:resources" --icon resources/logo.icns \
 --osx-bundle-identifier top.orii.exam

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

# 创建requirements.txt
.PHONY: requirements
requirements:
    @echo "生成 requirements.txt..."
    @echo "# Python packages for Exam System" > requirements.txt
    @echo "PySide6" >> requirements.txt
    @echo "pyyaml" >> requirements.txt
    @echo "pyinstaller" >> requirements.txt
    @echo "pycryptodome" >> requirements.txt
    @echo "requirements.txt 已生成!"

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

# 构建并运行
.PHONY: run
run: build
	@echo "运行可执行文件..."
	open "$(DIST_DIR)/$(APP_NAME).app"

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
    @echo "  make run          - 构建并运行"
    @echo "  make dmg          - 生成DMG安装镜像"
    @echo "  make dev          - 开发模式运行"
    @echo "  make clean        - 清理构建文件"
    @echo "  make package      - 创建发布包"
    @echo "  make check-deps  - 检查依赖包"
    @echo "  make test         - 运行测试"
    @echo "  make help          - 显示此帮助信息"
    @echo "  make obfuscate    - 使用 PyArmor 导出混淆代码到 obf/"
    @echo "  make build-secure - 使用 PyArmor 打包（包含代码混淆）"
# 生成密钥文件
.PHONY: genkey
genkey:
	@echo "生成密钥文件..."
	@if [ -f serect_key.py ]; then \
		echo "密钥已存在，跳过"; \
	else \
		if [ -f .env ]; then \
			ENV_KEY_B64=$$(grep -E '^AES_KEY_B64=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			ENV_KEY=$$(grep -E '^AES_KEY=' .env | head -n1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' '); \
			if [ -n "$$ENV_KEY_B64" ]; then \
				echo "使用 .env 中的 AES_KEY_B64"; \
				printf "AES_KEY = '%s'\n" "$$ENV_KEY_B64" > serect_key.py; \
				echo "serect_key.py 已生成"; \
			elif [ -n "$$ENV_KEY" ]; then \
				echo "使用 .env 中的 AES_KEY"; \
				printf "AES_KEY = '%s'\n" "$$ENV_KEY" > serect_key.py; \
				echo "serect_key.py 已生成"; \
			else \
				python3 -c "import os, base64; key=os.urandom(32); open('conf/serect_key.py','w').write('AES_KEY = ' + repr(base64.b64encode(key).decode('ascii')) + '\n'); print('serect_key.py 已生成')"; \
			fi; \
		else \
			python3 -c "import os, base64; key=os.urandom(32); open('conf/serect_key.py','w').write('AES_KEY = ' + repr(base64.b64encode(key).decode('ascii')) + '\n'); print('serect_key.py 已生成')"; \
		fi; \
	fi
