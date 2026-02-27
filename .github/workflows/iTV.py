import requests
import re

API_URL = "http://122.96.52.19:29010/tagNewestEpgList/JS_CUCC/1/100/0.json"

def classify(name):
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
    return '其他频道'

def fetch_and_generate():
    resp = requests.get(API_URL, timeout=10)
    data = resp.json()
    # 假设 data 是 {"data": [{"channelName": "...", "streamUrl": "..."}]}
    items = data.get('data', [])
    
    channels = []
    for item in items:
        name = item.get('channelName') or item.get('name')
        url = item.get('streamUrl') or item.get('url')
        if name and url:
            channels.append((name.strip(), url.strip()))
    
    groups = {}
    for name, url in channels:
        g = classify(name)
        groups.setdefault(g, []).append((name, url))
    
    # 生成 M3U
    with open('IPTV.m3u', 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for group, chs in groups.items():
            for name, url in chs:
                f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{group}",{name}\n')
                f.write(f'{url}\n')
    
    # 生成 TXT
    with open('IPTV.txt', 'w', encoding='utf-8') as f:
        for group, chs in groups.items():
            for name, url in chs:
                f.write(f'{name},{url}\n')
    
    print("生成完成：IPTV.m3u 和 IPTV.txt")

if __name__ == '__main__':
    fetch_and_generate()
