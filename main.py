import asyncio
import yaml
import datetime
from typing import Dict, Any
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("meeting_manager", "Ausert", "课题组组会管理工具", "0.0.1")
class meeting_manager(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.reminder_tasks: Dict[str, asyncio.Task] = {}
        self.config_data: Dict[str, Any] = {}
        self.next_reminder_times: Dict[str, datetime.datetime] = {}

    async def initialize(self):
        """插件初始化时加载配置并启动定时任务"""
        try:
            await self.load_config()
            await self.start_all_reminders()
            logger.info("定时提醒插件初始化完成")
        except Exception as e:
            logger.error(f"插件初始化失败: {e}")

    async def load_config(self):
        """加载配置文件"""
        try:
            with open("config.yml", "r", encoding="utf-8") as f:
                self.config_data = yaml.safe_load(f)
            logger.info("配置文件加载成功")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self.config_data = {}

    def parse_repeat_interval(self, repeat_str: str) -> datetime.timedelta:
        """解析重复时间间隔字符串，格式：天:时:分:秒"""
        try:
            parts = repeat_str.split(":")
            if len(parts) == 4:
                days, hours, minutes, seconds = map(int, parts)
                return datetime.timedelta(
                    days=days, hours=hours, minutes=minutes, seconds=seconds
                )
            else:
                logger.warning(f"无效的重复时间格式: {repeat_str}")
                return datetime.timedelta(days=1)
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
            repeat_times = reminder_config.get("repeat_times", -1)

            # 解析时间
            base_time = datetime.datetime.strptime(base_time_str, "%Y-%m-%d %H:%M:%S")
            repeat_interval = self.parse_repeat_interval(repeat_str)

            # 计算下次提醒时间
            next_time = self.calculate_next_reminder_time(base_time, repeat_interval)
            self.next_reminder_times[reminder_name] = next_time

            logger.info(f"提醒 {reminder_name} 将在 {next_time} 发送")

            times_sent = 0

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
        attention_config = self.config_data.get("attention", {})

        for reminder_name, reminder_config in attention_config.items():
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

    @filter.command("reminder_test")
    async def reminder_test(self, event: AstrMessageEvent):
        """测试提醒功能"""
        try:
            attention_config = self.config_data.get("attention", {})
            if not attention_config:
                yield event.plain_result("当前没有配置任何提醒")
                return

            # 发送测试消息
            for reminder_name, reminder_config in attention_config.items():
                message = reminder_config.get("message", "测试提醒")
                yield event.plain_result(f"测试提醒 '{reminder_name}': {message}")

        except Exception as e:
            logger.error(f"测试提醒失败: {e}")
            yield event.plain_result(f"测试提醒失败: {e}")

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

            # 启动新任务
            await self.start_all_reminders()

            yield event.plain_result("配置文件已重新加载")

        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            yield event.plain_result(f"重新加载配置失败: {e}")

    @filter.command_group("data")
    def data():
        """和数据有关的指令组。仅/data 会输出相关help内容"""
        print("有关数据操作的指令组抬头。")
        pass

    @data.command("members")
    def members():
        """和成员有关的指令组。"""
        print("有关成员操作的指令组抬头。")
        pass

    @data.command("reading_group")
    def reading_group():
        """管理reading group有关的指令"""
        print("有关reading group操作的指令组抬头。")
        pass

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!")

    async def terminate(self):
        """插件销毁时停止所有定时任务"""
        try:
            await self.stop_all_reminders()
            logger.info("定时提醒插件已停止")
        except Exception as e:
            logger.error(f"停止插件时发生错误: {e}")
