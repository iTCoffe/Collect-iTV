#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import sys

# 分类规则（根据频道名称关键字匹配）
def classify_channel(name):
    name_lower = name.lower()
    if re.search(r'cctv|中央', name_lower):
        return '央视频道'
    if '卫视' in name:
        return '卫视频道'
    if re.search(r'教育|cetv', name_lower):
        return '教育频道'
    if re.search(r'少儿|卡通|kids', name_lower):
        return '少儿频道'
    if '江苏' in name:
        return '江苏频道'
    if '南京' in name:
        return '南京频道'
    return '其他频道'  # 未匹配的频道归入其他

def fetch_and_generate_m3u(api_url, output_file='channels.m3u'):
    try:
        print(f"正在获取数据: {api_url}")
        response = requests.get(api_url, timeout=15)
        response.encoding = 'utf-8'
        data = response.json()
    except Exception as e:
        print(f"请求失败: {e}")
        return

    # 定位频道列表（兼容多种JSON结构）
    channel_list = None
    if isinstance(data, dict):
        # 尝试常见字段名
        for key in ['data', 'list', 'channels', 'programs', 'items']:
            if key in data and isinstance(data[key], list):
                channel_list = data[key]
                break
        if channel_list is None:
            # 遍历寻找第一个列表
            for key, value in data.items():
                if isinstance(value, list):
                    channel_list = value
                    break
    elif isinstance(data, list):
        channel_list = data

    if not channel_list:
        print("未能找到频道列表数据")
        return

    # 确定频道名称和URL的字段名
    name_field = None
    url_field = None
    possible_name_fields = ['channelName', 'name', 'title', 'channel_name', 'chname']
    possible_url_fields = ['streamUrl', 'url', 'stream_url', 'playUrl', 'play_url', 'm3u8', 'hls', 'liveUrl']

    if channel_list and isinstance(channel_list[0], dict):
        sample = channel_list[0]
        for field in possible_name_fields:
            if field in sample:
                name_field = field
                break
        for field in possible_url_fields:
            if field in sample:
                url_field = field
                break

    # 如果未能识别，尝试使用字典的前两个字段
    if name_field is None or url_field is None:
        if channel_list and isinstance(channel_list[0], dict):
            keys = list(sample.keys())
            if len(keys) >= 2:
                name_field = keys[0]
                url_field = keys[1]
                print(f"自动使用字段: name='{name_field}', url='{url_field}'")
            else:
                print("字典字段不足，无法解析")
                return
        else:
            print("频道列表格式异常")
            return

    # 初始化分组
    groups = {
        '央视频道': [],
        '卫视频道': [],
        '教育频道': [],
        '少儿频道': [],
        '江苏频道': [],
        '南京频道': [],
        '其他频道': []
    }

    for item in channel_list:
        if not isinstance(item, dict):
            continue
        name = item.get(name_field, '').strip()
        url = item.get(url_field, '').strip()
        if not name or not url:
            continue
        group = classify_channel(name)
        groups[group].append((name, url))

    # 写入M3U文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for group_name, channels in groups.items():
            for name, url in channels:
                f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{group_name}",{name}\n')
                f.write(f'{url}\n')

    total = sum(len(v) for v in groups.values())
    print(f"\n成功生成 {output_file}，共 {total} 个频道。")
    for group, chs in groups.items():
        if chs:
            print(f"  {group}: {len(chs)}")

if __name__ == '__main__':
    api_url = "http://122.96.52.19:29010/tagNewestEpgList/JS_CUCC/1/100/0.json"
    output_file = "channels.m3u"
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    fetch_and_generate_m3u(api_url, output_file)
