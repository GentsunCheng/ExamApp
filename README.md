# 本地内网考试系统（PySide6）

基于 PySide6 的桌面考试系统，面向内网环境。管理员端可配置试题与用户，通过 `sshpass` + `rsync` 将题库数据库同步到内网设备，考试完成后管理员可一键拉取各设备成绩并自动合并。

## 主要功能

- 登录与权限：管理员、普通用户两种角色
- 管理员
  - 用户管理：新增/删除、角色切换、启用/禁用、可选“姓名”字段；支持用户 Excel 模板导出与 Excel 导入
  - 试题管理：创建试题、支持“永久有效”，限时默认 60 分钟
  - 题目导入/导出：支持 Excel 模板（默认）与 JSON/YAML/TOML；提供 Excel 题目示例一键导出
  - 同步管理：配置设备并批量推送题库或拉取成绩，实时日志、进度对话框提示；支持设备 Excel 模板导出与 Excel 导入
  - 成绩总览与导出：查看所有用户的考试记录、是否通过；支持导出成绩为 Excel（通过标绿、未通过标红）
- 普通用户
  - 可选试题列表与历史成绩（显示考试标题）
  - 现代化考试界面：计时器、进度条、题目导航、自动保存

## 运行环境

- Python 3.9+
- PySide6
- 可选：`sshpass`、`rsync`（用于内网设备同步）

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt  # 如无该文件，可手动安装 pyside6、pyyaml、toml、openpyxl
```

## 启动

```bash
python3 main.py
```

## 默认管理员

- 用户名：`admin`
- 密码：`admin`
  登录后可创建普通用户或新的管理员。

## 数据存储

- 数据库路径：`~/.exam_system/exam.db`
- 拉取的远端数据库副本：`~/.exam_system/pulled/<设备IP>/`

## 同步说明

- 推送题库：将本地 SQLite 数据库通过 `rsync` 上传到目标设备的远端路径（如 `~/exam_system/exam.db`）
- 拉取成绩：从设备拉取数据库文件并合并到本地（attempts/attempt_answers）
- 设备配置字段：
  - 名称、IP、用户名、远程路径、SSH密码（可选）
- 支持无密码（密钥）或 `sshpass` 密码方式

## 试题与题目

- 创建试题时可选择“永久有效”，此时不需设置结束日期；否则选择具体的结束日期与时间
- 限时默认 60 分钟，可在创建时调整
- 及格比例以百分比输入（0-100），内部按 0-1 存储

## 导入/导出格式

### Excel（推荐）

- 工作表名称：`Questions`（如不存在则读取活动表）
- 表头（第一行）：`类型`、`内容`、`正确答案`、`分数`、`选项A`、`选项B`、`选项C`、`选项D`…（选项列可变，遇到空白停止读取）
- 类型取值：`单选` / `多选` / `判断`（也支持 `single` / `multiple` / `truefalse`）
- 正确答案：
  - 单选：填字母，如 `A`
  - 多选：用逗号分隔，如 `A,C`（支持中文逗号 `，`）
  - 判断：填 `true` 或 `false`（大小写不敏感）
- 选项：从 `选项A` 开始依次填写；`判断`题不需要选项
- 分数：在“分数”列填写数值；留空或格式不正确默认 `1` 分

操作入口：

- 在“试题”页面：
  - 选择试题后点击 `导入题目`，选择 Excel 文件（默认筛选 `.xlsx`）
  - 点击 `导出题目示例`，生成包含示例题目的 Excel 文件（含“分数”列）
- 在“成绩”页面：点击 `导出成绩Excel`，生成包含考试标题、分数与通过标识的 Excel 文件（通过为绿色、未通过为红色）
- 在“用户”页面：支持 `导出用户Excel模板`与 `从Excel导入用户`（导入时校验用户名/密码为 ASCII）
- 在“同步”页面：支持 `导出设备Excel模板`与 `从Excel导入设备`
- JSON：

```json
[
  {"type":"single","text":"2+2=?","options":[{"key":"A","text":"4"},{"key":"B","text":"3"}],"correct":["A"],"score":2},
  {"type":"multiple","text":"下列哪些是偶数?","options":[{"key":"A","text":"2"},{"key":"B","text":"3"},{"key":"C","text":"4"}],"correct":["A","C"],"score":3},
  {"type":"truefalse","text":"Python是解释型语言","correct":[true],"score":1}
]
```

- YAML：

```yaml
- type: single
  text: "2+2=?"
  score: 2
  options:
    - key: A
      text: "4"
    - key: B
      text: "3"
  correct:
    - A
```

- TOML：

```toml
[[questions]]
type = "single"
text = "2+2=?"
score = 2
[[questions.options]]
key = "A"
text = "4"
[[questions.options]]
key = "B"
text = "3"
correct = ["A"]
```

## 界面与体验

- 统一主题与配色、圆角卡片化布局、表格行 hover/选中高亮
- 下拉框、日期/时间控件、日历弹窗样式已现代化处理
- 同步过程提供非阻塞进度对话框，完成后自动关闭

## 开发说明

- 数据库迁移在程序启动时自动执行（如新增 `users.full_name`、`sync_targets.ssh_password`）
- 按需扩展题型或评分规则，在 `models.py` 与考试界面进行调整

## 版本控制

- 项目内置 `.gitignore`，忽略常见缓存、构建产物、虚拟环境与临时文件

## 注意事项

- 请勿在仓库中提交真实设备的 SSH 密码或数据库文件
- 内网设备路径与权限需提前配置好，确保 `rsync/ssh` 可访问

## 编译与打包教程

- 前置准备
  - 安装依赖：`make install` 或 `pip3 install -r requirements.txt`
  - 生成密钥：`make genkey`（生成 `serect_key.py`，用于 AES-GCM 加密解密；文件已被 `.gitignore` 忽略）
  - 准备资源：在项目根的 `resources/` 目录放置 `sshpass_darwin` 等平台二进制，并确保有执行权限；打包时会通过 `--add-data "resources:resources"` 进行携带
  - Python 版本：`3.9+`
- 开发模式
  - 直接运行：`python main.py`
  - 使用 Make：`make dev`
- 构建应用（PyInstaller）
  - 构建：`make build`
  - 结果：`dist/ExamSystem.app`（macOS 应用包），使用 `--onedir --windowed` 等参数生成
- 生成 DMG 安装镜像
  - 命令：`make dmg`
  - 结果：`dist/ExamSystem.dmg`
- 发布压缩包
  - 命令：`make package`
  - 结果：`dist/ExamSystem-YYYYMMDD.tar.gz`
- 依赖检查
  - 命令：`make check-deps`
- 清理与重置
  - 清理构建：`make clean`
  - 深度清理（含数据库目录）：`make deep-clean`

### 无 Make 环境的构建脚本

- 提供 `build.sh`，用于在没有 `make` 的设备上进行构建与发布。
- 使用方法：
  - 赋予执行权限：`chmod +x build.sh`
  - 安装依赖：`./build.sh install`
  - 生成密钥：`./build.sh genkey`
  - 构建应用：`./build.sh build`（产物：`dist/ExamSystem.app`）
  - 运行应用：`./build.sh run`
  - 生成 DMG：`./build.sh dmg`（产物：`dist/ExamSystem.dmg`）
  - 开发运行：`./build.sh dev`
  - 清理：`./build.sh clean` / `./build.sh deep-clean`
  - 依赖检查：`./build.sh check-deps`

### 加密密钥与数据说明

- 系统使用 `PyCryptodome` 的 AES-GCM 对部分字段加密存储（如试题标题/描述、题目文本/选项/答案、用户姓名、作答选项、SSH 密码等）。
- 加密密钥保存在 `conf/serect_key.py` 中的 `AES_KEY`（Base64 字符串）。
- 重要：请在首次运行或打包前执行 `make genkey` 生成密钥，并妥善备份；密钥一旦丢失，将无法解密已加密的数据。
- 出于安全考虑，`serect_key.py` 已在 `.gitignore` 中忽略，不会进入版本库或发布包。

### 使用 .env 指定密钥

- 支持在项目根的 `.env` 中预置密钥，`genkey` 将优先使用 `.env` 中的值：
  - `AES_KEY_B64`：32 字节密钥的 Base64 字符串（推荐）
  - 或 `AES_KEY`：同样为 Base64 字符串
- 示例 `.env`：

```
AES_KEY_B64=3GkYxvQfJ9qS8C4QGqGm8uQp3v9Qk7CqA1l7c0Qx1nY=
```

- 生成示例密钥命令：

```
python3 -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())'
```

- 运行 `make genkey` 或 `./build.sh genkey` 时：
  - 若 `.env` 存在且定义了 `AES_KEY_B64` 或 `AES_KEY`，将使用该值生成 `serect_key.py`
  - 若未定义，则自动生成新的随机密钥并写入 `serect_key.py`
