# 构建与发布

## Make 方式

- 安装依赖：`make install`
- 开发模式运行：`make dev`
- 构建应用（PyInstaller）：`make build`
- 构建并运行：`make run`
- 生成 DMG：`make dmg`
- 依赖检查：`make check-deps`
- 清理构建：`make clean`
- 深度清理（含数据库目录）：`make deep-clean`

## 无 Make 环境的构建脚本

项目提供 `build.sh`，用于在没有 `make` 的设备上进行构建与发布：

- 安装依赖：`./build.sh install`
- 开发运行：`./build.sh dev`
- 构建应用：`./build.sh build`（产物：`dist/ExamSystem.app`）
- 运行应用：`./build.sh run`
- 生成 DMG：`./build.sh dmg`（产物：`dist/ExamSystem.dmg`）
- 清理：`./build.sh clean` / `./build.sh deep-clean`
- 依赖检查：`./build.sh check-deps`

## 加密密钥与数据说明

系统使用 `PyCryptodome` 的 AES-GCM 对部分字段加密存储（如试题标题/描述、题目文本/选项/答案、用户姓名、作答选项、SSH 密码等）。

- 密钥文件：`conf/serect_key.py`
- 重要：首次运行或打包前执行 `make genkey` 或 `./build.sh genkey` 生成密钥，并妥善备份；密钥一旦丢失，将无法解密已加密的数据

### 使用 `.env` 指定密钥

支持在项目根的 `.env` 中预置密钥，`genkey` 将优先使用 `.env` 中的值：

- `AES_KEY_B64`：32 字节密钥的 Base64 字符串（推荐）
- 或 `AES_KEY`：同样为 Base64 字符串

示例 `.env`：

```text
AES_KEY_B64=3GkYxvQfJ9qS8C4QGqGm8uQp3v9Qk7CqA1l7c0Qx1nY=
```

生成示例密钥命令：

```bash
python3 -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())'
```

