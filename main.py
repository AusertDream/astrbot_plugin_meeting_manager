import asyncio
import random
import yaml
import datetime
import json
import shlex
from typing import Dict, List, Any
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("meeting_manager", "Ausert", "课题组组会管理工具", "0.0.2")
class meeting_manager(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.reminder_tasks: Dict[str, asyncio.Task] = {}
        self.config_data: Dict[str, Any] = {}
        self.next_reminder_times: Dict[str, datetime.datetime] = {}
        self.config_file = "config.yml"
        self.dynamic_config_file = "dynamic_config.yml"

    @property
    def attention_config(self) -> Dict[str, Any]:
        """获取attention配置"""
        return self.config_data.get("attention", {})

    async def initialize(self):
        """插件初始化时加载配置并启动定时任务"""
        try:
            await self.load_config()
            await self.load_dynamic_config()
            await self.start_all_reminders()
            logger.info("定时提醒插件初始化完成")
        except Exception as e:
            logger.error(f"插件初始化失败: {e}")

    async def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config_data = yaml.safe_load(f)
            logger.info("配置文件加载成功")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self.config_data = {}

    def _load_dynamic_config_data(self) -> Dict[str, Any]:
        """读取动态配置文件数据"""
        try:
            with open(self.dynamic_config_file, "r", encoding="utf-8") as f:
                dynamic_config = yaml.safe_load(f)
                return dynamic_config if dynamic_config else {"attention": {}}
        except FileNotFoundError:
            return {"attention": {}}
        except Exception as e:
            logger.error(f"读取动态配置失败: {e}")
            return {"attention": {}}

    async def load_dynamic_config(self):
        """加载动态配置文件"""
        try:
            dynamic_config = self._load_dynamic_config_data()
            if dynamic_config and "attention" in dynamic_config:
                # 合并动态配置到主配置
                if "attention" not in self.config_data:
                    self.config_data["attention"] = {}
                self.config_data["attention"].update(dynamic_config["attention"])
            logger.info("动态配置文件加载成功")
        except FileNotFoundError:
            logger.info("动态配置文件不存在，将创建新文件")
        except Exception as e:
            logger.error(f"动态配置文件加载失败: {e}")

    def _save_dynamic_config_data(self, dynamic_config: Dict[str, Any]):
        """保存动态配置数据到文件"""
        try:
            with open(self.dynamic_config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    dynamic_config, f, default_flow_style=False, allow_unicode=True
                )
            logger.info("动态配置保存成功")
        except Exception as e:
            logger.error(f"保存动态配置失败: {e}")
            raise

    def _validate_time_format(self, time_str: str) -> bool:
        """验证时间格式"""
        try:
            datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False

    def _validate_repeat_format(self, repeat_str: str) -> bool:
        """验证重复间隔格式"""
        try:
            parts = repeat_str.split(":")
            if len(parts) != 4:
                return False
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False

    def validate_reminder_params(
        self,
        name: str,
        sid: List[str],
        time_str: str,
        repeat_str: str,
        repeat_times: int,
        message: str,
    ) -> tuple[bool, str]:
        """验证提醒参数"""
        # 检查名称
        if not name or not name.strip():
            return False, "提醒名称不能为空"

        # 检查sid
        if not sid or not isinstance(sid, list):
            return False, "sid必须是非空列表"

        # 检查时间格式
        if not self._validate_time_format(time_str):
            return False, f"时间格式错误: {time_str}，正确格式: YYYY-MM-DD HH:MM:SS"

        # 检查重复间隔格式
        if not self._validate_repeat_format(repeat_str):
            return False, f"重复间隔格式错误: {repeat_str}，正确格式: 天:时:分:秒"

        # 检查重复次数
        if not isinstance(repeat_times, int) or repeat_times < -1:
            return False, "重复次数必须是大于等于-1的整数"

        # 检查消息
        if not message or not message.strip():
            return False, "提醒消息不能为空"

        return True, "参数验证通过"

    def _parse_command_parts(self, message_str: str, expected_parts: int) -> List[str]:
        """解析命令参数，支持带引号的参数"""
        try:
            # 使用 shlex 来正确处理带引号的参数
            parts = shlex.split(message_str)
            return parts if len(parts) >= expected_parts else []
        except ValueError:
            # 如果 shlex 解析失败，回退到原来的方法
            parts = message_str.split(maxsplit=expected_parts - 1)
            return parts if len(parts) >= expected_parts else []

    @filter.command("reminder_add")
    async def reminder_add(self, event: AstrMessageEvent):
        """添加新的提醒任务
        用法: /reminder_add <名称> <sid列表> <时间> <重复间隔> <重复次数> <消息>
        示例: /reminder_add test1 [123,456] "2025-01-20 19:30:00" "7:00:00:00" 10 "测试提醒"
        """
        try:
            parts = self._parse_command_parts(event.message_str.strip(), 7)
            if len(parts) < 7:
                yield event.plain_result(
                    "参数不足！用法: /reminder_add <名称> <sid列表> <时间> <重复间隔> <重复次数> <消息>\n"
                    '示例: /reminder_add test1 [123,456] "2025-01-20 19:30:00" "7:00:00:00" 10 "测试提醒"'
                )
                return

            name = parts[1]
            sid_str = parts[2]
            time_str = parts[3]
            repeat_str = parts[4]
            repeat_times_str = parts[5]
            message = parts[6]

            # 解析sid列表
            try:
                # 尝试JSON格式解析
                sid = json.loads(sid_str)
                if not isinstance(sid, list):
                    raise ValueError("sid必须是列表")
            except (json.JSONDecodeError, ValueError):
                # 尝试Python列表格式解析
                try:
                    # 移除可能的方括号，按逗号分割
                    clean_sid_str = sid_str.strip()
                    if clean_sid_str.startswith("[") and clean_sid_str.endswith("]"):
                        clean_sid_str = clean_sid_str[1:-1]

                    # 按逗号分割并清理引号
                    sid_items = []
                    for item in clean_sid_str.split(","):
                        item = item.strip().strip("'\"")
                        if item:
                            sid_items.append(item)

                    if not sid_items:
                        raise ValueError("sid列表不能为空")

                    sid = sid_items
                except Exception as e:
                    yield event.plain_result(
                        f'sid格式错误: {e}。支持格式: [123,456] 或 ["user1","user2"]'
                    )
                    return

            # 解析重复次数
            try:
                repeat_times = int(repeat_times_str)
            except ValueError:
                yield event.plain_result("重复次数必须是整数")
                return

            # 验证参数
            is_valid, error_msg = self.validate_reminder_params(
                name, sid, time_str, repeat_str, repeat_times, message
            )

            if not is_valid:
                yield event.plain_result(f"参数验证失败: {error_msg}")
                return

            # 检查名称是否已存在
            if name in self.attention_config:
                yield event.plain_result(f"提醒名称 '{name}' 已存在，请使用其他名称")
                return

            # 创建新提醒配置
            new_reminder = {
                "sid": sid,
                "time": time_str,
                "repeat": repeat_str,
                "repeat_times": repeat_times,
                "message": message,
            }

            # 添加到配置
            if "attention" not in self.config_data:
                self.config_data["attention"] = {}
            self.config_data["attention"][name] = new_reminder

            # 保存到动态配置文件
            dynamic_config = self._load_dynamic_config_data()
            dynamic_config["attention"][name] = new_reminder
            self._save_dynamic_config_data(dynamic_config)
            logger.info(f"动态配置已保存，新增提醒: {name}")

            # 启动新提醒任务
            task = asyncio.create_task(self.reminder_loop(name, new_reminder))
            self.reminder_tasks[name] = task

            yield event.plain_result(f"提醒 '{name}' 添加成功！")

        except Exception as e:
            logger.error(f"添加提醒失败: {e}")
            yield event.plain_result(f"添加提醒失败: {e}")

    @filter.command("reminder_del")
    async def reminder_del(self, event: AstrMessageEvent):
        """删除提醒任务
        用法: /reminder_del <名称>
        示例: /reminder_del test1
        """
        try:
            parts = self._parse_command_parts(event.message_str.strip(), 2)
            if len(parts) < 2:
                yield event.plain_result("用法: /reminder_del <名称>")
                return

            name = parts[1]

            # 检查提醒是否存在
            if name not in self.attention_config:
                yield event.plain_result(f"提醒 '{name}' 不存在")
                return

            # 停止任务
            if name in self.reminder_tasks:
                try:
                    self.reminder_tasks[name].cancel()
                    await self.reminder_tasks[name]
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"停止提醒任务 {name} 失败: {e}")

                del self.reminder_tasks[name]

            # 从配置中删除
            del self.config_data["attention"][name]

            # 从下次提醒时间中删除
            if name in self.next_reminder_times:
                del self.next_reminder_times[name]

            # 更新动态配置文件
            dynamic_config = self._load_dynamic_config_data()
            if name in dynamic_config["attention"]:
                del dynamic_config["attention"][name]
            self._save_dynamic_config_data(dynamic_config)
            logger.info(f"动态配置已更新，删除提醒: {name}")

            yield event.plain_result(f"提醒 '{name}' 删除成功！")

        except Exception as e:
            logger.error(f"删除提醒失败: {e}")
            yield event.plain_result(f"删除提醒失败: {e}")

    @filter.command("reminder_list")
    async def reminder_list(self, event: AstrMessageEvent):
        """列出所有提醒任务"""
        try:
            if not self.attention_config:
                yield event.plain_result("当前没有配置任何提醒")
                return

            list_msg = "当前所有提醒任务:\n"
            for name, config in self.attention_config.items():
                status = "运行中" if name in self.reminder_tasks else "已停止"
                next_time = self.next_reminder_times.get(name, "未知")
                if isinstance(next_time, datetime.datetime):
                    next_time = next_time.strftime("%Y-%m-%d %H:%M:%S")

                list_msg += f"\n📅 {name} ({status})\n"
                list_msg += f"   消息: {config.get('message', 'N/A')}\n"
                list_msg += f"   下次提醒: {next_time}\n"
                list_msg += f"   重复: {config.get('repeat', 'N/A')}\n"
                list_msg += f"   剩余次数: {config.get('repeat_times', 'N/A')}\n"

            yield event.plain_result(list_msg)

        except Exception as e:
            logger.error(f"列出提醒失败: {e}")
            yield event.plain_result(f"列出提醒失败: {e}")

    def parse_repeat_interval(self, repeat_str: str) -> datetime.timedelta:
        """解析重复时间间隔字符串，格式：天:时:分:秒"""
        if not self._validate_repeat_format(repeat_str):
            logger.warning(f"无效的重复时间格式: {repeat_str}")
            return datetime.timedelta(days=1)

        try:
            parts = repeat_str.split(":")
            days, hours, minutes, seconds = map(int, parts)
            return datetime.timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            )
        except Exception as e:
            logger.error(f"解析重复时间失败: {e}")
            return datetime.timedelta(days=1)

    def calculate_next_reminder_time(
        self, base_time: datetime.datetime, repeat_interval: datetime.timedelta
    ) -> datetime.datetime:
        """计算下次提醒时间"""
        now = datetime.datetime.now()
        if base_time <= now:
            # 如果基础时间已过，计算下一个符合的时间点
            time_diff = now - base_time
            intervals_passed = time_diff // repeat_interval + 1
            next_time = base_time + (repeat_interval * intervals_passed)
        else:
            next_time = base_time

        # 随机调整1~40秒
        random_adjustment = random.randint(1, 40)
        next_time = next_time + datetime.timedelta(seconds=random_adjustment)

        return next_time

    async def send_reminder(self, reminder_name: str, reminder_config: Dict[str, Any]):
        """发送提醒消息，sid可为用户ID或群聊ID"""
        try:
            message = reminder_config.get("message", "提醒时间到了！")
            sids = reminder_config.get("sid", [])

            for sid in sids:
                try:
                    # 优先尝试私聊
                    await self.context.send_private_message(sid, message)
                    logger.info(f"已向用户 {sid} 发送提醒: {message}")
                except Exception as e_user:
                    try:
                        # 私聊失败则尝试群聊
                        await self.context.send_group_message(sid, message)
                        logger.info(f"已向群聊 {sid} 发送提醒: {message}")
                    except Exception as e_group:
                        logger.error(
                            f"向sid {sid} 发送消息失败: 用户错误: {e_user}，群聊错误: {e_group}"
                        )
        except Exception as e:
            logger.error(f"发送提醒失败: {e}")

    async def reminder_loop(self, reminder_name: str, reminder_config: Dict[str, Any]):
        """单个提醒的循环任务"""
        try:
            base_time_str = reminder_config.get("time")
            repeat_str = reminder_config.get("repeat", "1:00:00:00")
            repeat_times = reminder_config.get("repeat_times", 0)

            # 解析时间
            base_time = datetime.datetime.strptime(base_time_str, "%Y-%m-%d %H:%M:%S")
            repeat_interval = self.parse_repeat_interval(repeat_str)

            now = datetime.datetime.now()
            # 计算下次提醒时间
            next_time = self.calculate_next_reminder_time(base_time, repeat_interval)

            # 判断是否已经超过最大提醒次数
            if repeat_times > 0 and repeat_interval.total_seconds() > 0:
                # 计算最大允许的提醒时间点
                max_time = base_time + repeat_interval * (repeat_times - 1)
                if next_time > max_time:
                    logger.info(f"提醒 {reminder_name} 所有提醒已过期，不再发送")
                    return
                # 计算已发送次数
                times_sent = (
                    next_time - base_time
                ).total_seconds() // repeat_interval.total_seconds()
            elif repeat_times > 0 and repeat_interval.total_seconds() == 0:
                # 只提醒一次
                if now > base_time:
                    logger.info(f"提醒 {reminder_name} 已过期，不再发送")
                    return
                times_sent = 0
            else:
                times_sent = 0

            self.next_reminder_times[reminder_name] = next_time
            logger.info(f"提醒 {reminder_name} 将在 {next_time} 发送")

            while True:
                now = datetime.datetime.now()
                if now >= next_time:
                    # 发送提醒
                    await self.send_reminder(reminder_name, reminder_config)
                    times_sent += 1

                    # 检查是否达到重复次数限制
                    if repeat_times > 0 and times_sent >= repeat_times:
                        logger.info(
                            f"提醒 {reminder_name} 已达到重复次数限制，停止发送"
                        )
                        break

                    # 计算下次提醒时间
                    next_time = next_time + repeat_interval
                    self.next_reminder_times[reminder_name] = next_time
                    logger.info(f"提醒 {reminder_name} 下次将在 {next_time} 发送")

                # 等待一段时间再检查
                await asyncio.sleep(60)  # 每分钟检查一次

        except asyncio.CancelledError:
            logger.info(f"提醒任务 {reminder_name} 已取消")
        except Exception as e:
            logger.error(f"提醒任务 {reminder_name} 执行失败: {e}")

    async def start_all_reminders(self):
        """启动所有提醒任务"""
        for reminder_name, reminder_config in self.attention_config.items():
            try:
                task = asyncio.create_task(
                    self.reminder_loop(reminder_name, reminder_config)
                )
                self.reminder_tasks[reminder_name] = task
                logger.info(f"已启动提醒任务: {reminder_name}")
            except Exception as e:
                logger.error(f"启动提醒任务 {reminder_name} 失败: {e}")

    async def stop_all_reminders(self):
        """停止所有提醒任务"""
        for task_name, task in self.reminder_tasks.items():
            try:
                task.cancel()
                await task
                logger.info(f"已停止提醒任务: {task_name}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"停止提醒任务 {task_name} 失败: {e}")

        self.reminder_tasks.clear()
        self.next_reminder_times.clear()

    @filter.command("reminder_status")
    async def reminder_status(self, event: AstrMessageEvent):
        """查看提醒状态"""
        try:
            if not self.next_reminder_times:
                yield event.plain_result("当前没有活跃的提醒任务")
                return

            status_msg = "当前提醒状态:\n"
            for reminder_name, next_time in self.next_reminder_times.items():
                status_msg += f"- {reminder_name}: 下次提醒时间 {next_time.strftime('%Y-%m-%d %H:%M:%S')}\n"

            yield event.plain_result(status_msg)

        except Exception as e:
            logger.error(f"获取提醒状态失败: {e}")
            yield event.plain_result(f"获取提醒状态失败: {e}")

    @filter.command("reminder_reload")
    async def reminder_reload(self, event: AstrMessageEvent):
        """重新加载配置文件"""
        try:
            # 停止现有任务
            await self.stop_all_reminders()

            # 重新加载配置
            await self.load_config()
            await self.load_dynamic_config()  # 重新加载动态配置

            # 启动新任务
            await self.start_all_reminders()

            yield event.plain_result("配置文件已重新加载")

        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            yield event.plain_result(f"重新加载配置失败: {e}")

    async def terminate(self):
        """插件销毁时停止所有定时任务"""
        try:
            await self.stop_all_reminders()
            logger.info("定时提醒插件已停止")
        except Exception as e:
            logger.error(f"停止插件时发生错误: {e}")
