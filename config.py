#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时提醒配置文件
支持多个提醒任务，每个任务可以有不同的配置
sid: 可以是用户ID或群聊ID，自动识别
"""

# 提醒配置字典
attention = {
    # 组会提醒示例
    "zuhui": {
        "sid": [
            "wechatpadpro:GroupMessage:47622585703@chatroom"
        ],  # 接收提醒的用户/群聊ID列表
        "time": "2025-07-24 19:00:00",  # 首次提醒时间，格式：YYYY-MM-DD HH:MM:SS
        "repeat": "7:00:00:00",  # 重复间隔，格式：天:时:分:秒
        "repeat_times": 100,  # 重复次数，-1表示无限重复
        "message": "还有半小时就要组会啦！请做好准备。",  # 提醒消息内容
    },
    "zhoubao": {
        "sid": [
            "wechatpadpro:GroupMessage:47622585703@chatroom"
        ],  # 接收提醒的用户/群聊ID列表
        "time": "2025-07-23 19:00:00",  # 首次提醒时间，格式：YYYY-MM-DD HH:MM:SS
        "repeat": "7:00:00:00",  # 重复间隔，格式：天:时:分:秒
        "repeat_times": 100,  # 重复次数，-1表示无限重复
        "message": "记得给老师发周报喵！",  # 提醒消息内容
    },
    # 每日打卡提醒示例
    "daily_checkin": {
        "sid": ["wechatpadpro:FriendMessage:wxid_tq8irwut2qpg22"],
        "time": "2025-01-20 09:00:01",
        "repeat": "1:00:00:00",  # 每天重复
        "repeat_times": -1,  # 无限重复
        "message": "早上好！请记得打卡签到。",
    },
    "test1": {
        "sid": ["wechatpadpro:FriendMessage:wxid_tq8irwut2qpg22"],
        "time": "2025-07-26 17:50:00",
        "repeat": "0:00:00:00",  # 不重复，只提醒一次
        "repeat_times": 1,
        "message": "这事一次测试喵.",
    },
    "test2": {
        "sid": [
            "wechatpadpro:FriendMessage:wxid_tq8irwut2qpg22",
            "wechatpadpro:GroupMessage:55997502173@chatroom",
        ],
        "time": "2025-07-26 17:50:20",
        "repeat": "0:00:00:00",  # 不重复，只提醒一次
        "repeat_times": 1,
        "message": "这事一次测试喵..",
    },
}

# 主配置字典
config = {"attention": attention}
