# 本地内网考试系统（PySide6）

基于 PySide6 的桌面考试系统，面向内网环境。管理员端可配置试题与用户，通过 `sshpass` + `rsync` 将题库数据库同步到内网设备，考试完成后管理员可一键拉取各设备成绩并自动合并。

## 主要功能
- 登录与权限：管理员、普通用户两种角色
- 管理员
  - 用户管理：新增/删除、角色切换、启用/禁用、可选“姓名”字段
  - 试题管理：创建试题、支持“永久有效”，限时默认 60 分钟
  - 题目导入/导出：支持 JSON/YAML/TOML 三种格式示例
  - 同步管理：配置设备并批量推送题库或拉取成绩，实时日志、进度对话框提示
  - 成绩总览：查看所有用户的考试记录与是否通过
- 普通用户
  - 可选试题列表与历史成绩
  - 现代化考试界面：计时器、进度条、题目导航、自动保存

## 运行环境
- Python 3.9+
- PySide6
- 可选：`sshpass`、`rsync`（用于内网设备同步）

## 安装
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt  # 如无该文件，可手动安装 pyside6、pyyaml、toml
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