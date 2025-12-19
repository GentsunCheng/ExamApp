# 本地内网考试系统（PySide6）

基于 PySide6 的桌面考试系统，面向内网环境。管理员端可配置试题与用户，通过 `sshpass` + `rsync` 将题库数据库同步到内网设备，考试完成后管理员可一键拉取各设备成绩并自动合并。

## 功能概览

- 管理员端：用户/试题/同步/成绩/学习进度（详见 `docs/features.md`）
- 用户端：考试与历史成绩、学习进度只读查看（详见 `docs/features.md`）

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

## 文档链接

- [快速开始](docs/quickstart.md)
- [功能概览](docs/features.md)
- [导入/导出](docs/import_export.md)
- [同步说明](docs/sync.md)
- [学习进度](docs/progress.md)
- [构建与发布](docs/build.md)
