# 课题组组会管理插件

适配对象：AstrBot 插件

---

## 功能特性

### 🔔 智能定时提醒
- **多任务支持**：可配置多个提醒任务，支持组会、打卡、周报等多场景
- **灵活时间设置**：支持精确到秒的定时提醒
- **智能重复**：支持按天、小时、分钟、秒的重复间隔
- **次数限制**：可设置重复次数，支持无限重复
- **动态管理**：支持运行时通过指令增删提醒任务，无需重启
- **群聊/私聊兼容**：sid 可为用户ID或群聊ID，自动适配发送方式
- **防刷屏机制**：每次提醒自动随机延迟1~40秒，防止多群/多用户同时刷屏
- **实时状态**：可随时查看提醒任务状态和下次提醒时间
- **热重载**：支持运行时重新加载配置文件
- **日志追踪**：详细记录提醒发送、异常、配置变更等

### 📊 数据管理
- **成员管理**：管理课题组成员信息
- **Reading Group管理**：管理读书小组相关事务

---

## 快速上手

### 1. 安装依赖
```bash
pip install -r requirements.txt
# 或
uv sync
```

### 2. 配置提醒任务
编辑 `config.yml`，参考下方示例。

### 3. 启动/重载插件
将插件部署到 AstrBot 插件目录，重启 AstrBot 或使用 `/reminder_reload` 热重载。

---

## 常用指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `/reminder_add` | 添加提醒 | `/reminder_add test1 [123,456] "2025-01-20 19:30:00" "7:00:00:00" 10 "测试提醒"` |
| `/reminder_del` | 删除提醒 | `/reminder_del test1` |
| `/reminder_list` | 列出所有提醒 | `/reminder_list` |
| `/reminder_status` | 查看下次提醒时间 | `/reminder_status` |
| `/reminder_reload` | 重新加载配置 | `/reminder_reload` |
| `/helloworld` | 测试插件 | `/helloworld` |

---

## 配置文件说明

### config.yml 示例

```yaml
attention:
  weekly_meeting:
    sid: [wechatpadpro:GroupMessage:123@chatroom]
    time: 2025-01-20 19:30:00
    repeat: "7:00:00:00"
    repeat_times: 100
    message: '还有半小时就要组会啦！请做好准备。'
  daily_checkin:
    sid: [wechatpadpro:FriendMessage:wxid_123]
    time: 2025-01-20 09:00:00
    repeat: "1:00:00:00"
    repeat_times: -1
    message: '早上好！请记得打卡签到。'
```

### 参数详解

- **sid**: 用户/群聊ID列表，支持 AstrBot 兼容格式
- **time**: 首次提醒时间，`YYYY-MM-DD HH:MM:SS`
- **repeat**: 重复间隔，`天:时:分:秒`，如 `7:00:00:00`
- **repeat_times**: 重复次数，正整数或 -1（无限）
- **message**: 提醒内容

### 动态配置
- 通过指令添加的提醒会自动保存到 `dynamic_config.yml`，重启后依然生效。

---

## 技术实现亮点

- `asyncio` 异步定时任务
- `datetime` 精确时间计算
- 随机延迟防刷屏
- 动态配置热更新
- 完善的异常与日志处理

---

## 常见问题（FAQ）

**Q: 为什么提醒没有发送？**  
A: 检查 sid 是否正确、时间格式是否正确、日志中是否有报错。

**Q: 如何只提醒一次？**  
A: `repeat: "0:00:00:00"` 且 `repeat_times: 1`

**Q: 如何群发到多个群/用户？**  
A: `sid` 列表中写多个ID即可。

**Q: 动态添加的提醒会丢失吗？**  
A: 不会，所有通过指令添加的提醒会自动保存到 `dynamic_config.yml`。

---

## 版本变更

- **v0.0.2**  
  - 优化代码结构，消除冗余
  - 支持动态指令管理提醒
  - 支持群聊/私聊自动适配
  - 增加防刷屏机制

---

## 支持与反馈

- [帮助文档](https://astrbot.app)
- 如有问题或建议，请提交 Issue 或 Pull Request

---

如需进一步美化或补充英文文档、贡献指南、API说明等，请告知！
