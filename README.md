[![Fork](https://img.shields.io/badge/Forked_From-Original_Project-lightgrey.svg)](https://github.com/NahidaBuer/Telegram-Channel-to-QQ)
[![Modified by AI](https://img.shields.io/badge/Modified_By-Gemini-blue.svg)](https://gemini.google.com)
> **Note:** This repository is a modified fork of [BiliBili_Livestream_Reminder](https://github.com/hydrotho/BiliBili_Livestream_Reminder). The modifications, refactoring, and new features introduced in this fork were primarily implemented using Gemini.
# BiliBili_Livestream_Reminder

一款监控哔哩哔哩直播间并通过 Telegram 机器人发送通知的工具。

## 简介

`BiliBili_Livestream_Reminder` 能够实时监控指定的哔哩哔哩直播间。当直播开始时，它会自动通过 Telegram API 发送包含开播时间、标题、主播名称和直播间链接的图文通知，确保您能够及时获取开播状态。

## 快速开始

### 环境要求

- [Python 3.12+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) (用于依赖与环境管理)

### 安装与配置

1. 克隆本仓库：
   ```shell
   git clone [https://github.com/](https://github.com/)<YOUR_USERNAME>/BiliBili_Livestream_Reminder.git
   cd BiliBili_Livestream_Reminder
   ```

2. 同步虚拟环境与依赖（依赖配置于 `pyproject.toml`）：
   ```shell
   uv sync
   ```

3. 准备配置文件：
   ```shell
   cp config.example.yaml config.yaml
   ```
   使用文本编辑器修改 `config.yaml`，填入您的 Telegram Bot Token、Chat ID 以及需要监控的 Bilibili 直播间 ID 列表。

### 使用

直接使用 `uv run` 启动监控程序：

```shell
uv run main.py --config config.yaml
```

> **提示**：若要在服务器后台保持运行，建议配合 `tmux`、`nohup` 或配置 `systemd` 服务使用。

## 支持

如果您遇到任何问题或有任何建议，欢迎提出 Issue。

## 许可证

本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。
