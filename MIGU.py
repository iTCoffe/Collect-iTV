import requests
import json
import time
import random
import hashlib
import re
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置参数
thread_num = 10  # 线程数
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://m.miguvideo.com",
    "Pragma": "no-cache",
    "Referer": "https://m.miguvideo.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Support-Pendant": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "sec-ch-ua": "\"Chromium\";v=\"136\", \"Microsoft Edge\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "terminalId": "h5"
}

# 分类配置
categories = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
category_dict = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8',
    '体育': '7538163cdac044398cb292ecf75db4e0',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05',
    '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b',
    '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c',
    '教育': 'af72267483d94275995a4498b2799ecd',
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d',
    '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede',
    '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}

# 全局变量
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"

def get_today_date():
    """获取当前日期，格式为年月日"""
    now = datetime.now()
    return f"{now.year}{now.month:02d}{now.day:02d}"

def md5_string(text):
    """计算MD5值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_salt_and_sign(pid):
    """生成salt和sign参数"""
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5_string(md5_string(app_t) + suffix)
    
    return {
        "salt": salt,
        "sign": sign,
        "timestamp": timestamp
    }

def extract_play_url(resp_data, pid):
    """从响应数据中提取播放URL"""
    try:
        if isinstance(resp_data, dict) and "body" in resp_data:
            body = resp_data["body"]
            # 尝试多种可能的URL路径
            url_paths = [
                "urlInfo.url",
                "urls.0.url",
                "data.url",
                "url"
            ]
            
            url = None
            for path in url_paths:
                parts = path.split(".")
                temp = body
                for part in parts:
                    if part in temp:
                        temp = temp[part]
                    else:
                        temp = None
                        break
                if temp and isinstance(temp, str) and temp.startswith("http"):
                    url = temp
                    break
            
            if url and "puData=" in url:
                return generate_720p_url(url, pid)
            elif url:
                return url
        return None
    except Exception as e:
        print(f"提取播放URL时出错: {e}")
        return None

def generate_720p_url(url, pid):
    """生成720p的URL"""
    try:
        match = re.search(r'puData=([^&]+)', url)
        if not match:
            return url
            
        puData = match.group(1)
        keys = "cdabyzwxkl"
        ddCalcu = []
        
        for i in range(0, min(int(len(puData) / 2), len(puData))):
            ddCalcu.append(puData[len(puData) - i - 1])
            ddCalcu.append(puData[i])
            
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                date_str = get_today_date()
                if len(date_str) > 2:
                    idx = int(date_str[2])
                    if idx < len(keys):
                        ddCalcu.append(keys[idx])
            if i == 3 and len(pid) > 6:
                idx = int(pid[6])
                if idx < len(keys):
                    ddCalcu.append(keys[idx])
            if i == 4:
                ddCalcu.append("a")
        
        ddCalcu_str = ''.join(ddCalcu)
        return f'{url}&ddCalcu={ddCalcu_str}&sv=10004&ct=android'
    except Exception as e:
        print(f"生成720p URL时出错: {e}")
        return url

def get_final_m3u8_url(url):
    """获取最终的m3u8 URL"""
    if not url:
        return None
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10, allow_redirects=False)
            
            # 检查重定向
            if 300 <= response.status_code < 400:
                location = response.headers.get('Location')
                if location and location.startswith('http'):
                    url = location
                    continue
            
            # 如果是m3u8文件，直接返回
            if 'm3u8' in url or response.headers.get('Content-Type', '').find('application/vnd.apple.mpegurl') != -1:
                return url
                
            # 解析内容寻找m3u8链接
            content = response.text
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and ('m3u8' in line or '.ts' in line):
                    if line.startswith('http'):
                        return line
                    elif line.startswith('/'):
                        # 构建完整URL
                        base_url = '/'.join(url.split('/')[:3])
                        return base_url + line
                    else:
                        # 相对路径
                        base_url = '/'.join(url.split('/')[:-1])
                        return base_url + '/' + line
                        
            time.sleep(0.5)  # 短暂等待后重试
            
        except requests.RequestException as e:
            print(f"获取m3u8 URL失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return None
    
    return url

def parse_channel_info(data):
    """解析频道信息"""
    try:
        # 尝试多种可能的字段
        channel_info = {
            "name": data.get("name") or data.get("channelName") or data.get("title") or "未知频道",
            "pid": data.get("pID") or data.get("contentId") or data.get("id") or "",
            "logo": None
        }
        
        # 获取logo
        pics = data.get("pics") or data.get("image") or {}
        if isinstance(pics, dict):
            channel_info["logo"] = pics.get("highResolutionH") or pics.get("large") or pics.get("normal")
        elif isinstance(pics, str):
            channel_info["logo"] = pics
        
        return channel_info
    except Exception as e:
        print(f"解析频道信息时出错: {e}")
        return {"name": "未知频道", "pid": "", "logo": ""}

def get_channel_play_url(pid):
    """获取频道播放URL"""
    try:
        # 使用POST请求获取播放信息
        params = generate_salt_and_sign(pid)
        rateType = "2" if pid == "608831231" else "3"  # 广东卫视特殊处理
        
        play_url_api = f"https://play.miguvideo.com/playurl/v1/play/playurl"
        
        payload = {
            "sign": params["sign"],
            "rateType": rateType,
            "contId": pid,
            "timestamp": params["timestamp"],
            "salt": params["salt"]
        }
        
        # 尝试使用简单的POST请求
        response = requests.post(
            play_url_api,
            data=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"API请求失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"获取频道播放URL时出错: {e}")
        return None

def process_channel(channel_info, category_name):
    """处理单个频道"""
    try:
        if not channel_info["pid"]:
            print(f'频道 [{channel_info["name"]}] PID为空，跳过')
            return None
        
        print(f'正在处理频道: {channel_info["name"]}')
        
        # 获取播放信息
        play_data = get_channel_play_url(channel_info["pid"])
        if not play_data:
            print(f'频道 [{channel_info["name"]}] 获取播放数据失败')
            return None
        
        # 提取播放URL
        play_url = extract_play_url(play_data, channel_info["pid"])
        if not play_url:
            print(f'频道 [{channel_info["name"]}] 提取播放URL失败')
            return None
        
        # 获取最终的m3u8 URL
        final_url = get_final_m3u8_url(play_url)
        if not final_url:
            print(f'频道 [{channel_info["name"]}] 获取最终播放URL失败')
            return None
        
        # 构建m3u条目
        m3u_entry = f'#EXTINF:-1 tvg-id="{channel_info["name"]}" tvg-name="{channel_info["name"]}" '
        if channel_info["logo"]:
            m3u_entry += f'tvg-logo="{channel_info["logo"]}" '
        m3u_entry += f'group-title="{category_name}",{channel_info["name"]}\n'
        m3u_entry += f'{final_url}\n'
        
        print(f'频道 [{channel_info["name"]}] 处理成功')
        return m3u_entry
        
    except Exception as e:
        print(f'处理频道 [{channel_info.get("name", "未知")}] 时出错: {e}')
        return None

def generate_m3u_file():
    """生成M3U文件"""
    print("开始生成M3U文件...")
    
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    # 生成M3U头部
    m3u_header = '''#EXTM3U x-tvg-url="https://cdn.jsdelivr.net/gh/develop202/migu_video/playback.xml,https://ghfast.top/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://hk.gh-proxy.org/raw.githubusercontent.com/develop202/migu_video/refs/heads/main/playback.xml,https://develop202.github.io/migu_video/playback.xml,https://raw.githubusercontents.com/develop202/migu_video/refs/heads/main/playback.xml" catchup="append" catchup-source="&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"

'''
    
    all_channels = []
    
    for category in categories:
        print(f"\n处理分类: {category}")
        
        # API URL
        api_url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{category_dict[category]}'
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"获取分类 {category} 失败，状态码: {response.status_code}")
                continue
                
            data = response.json()
            if "body" not in data or "dataList" not in data["body"]:
                print(f"分类 {category} 没有数据")
                continue
                
            channel_list = data["body"]["dataList"]
            print(f"找到 {len(channel_list)} 个频道")
            
            # 使用线程池处理频道
            with ThreadPoolExecutor(max_workers=thread_num) as executor:
                futures = []
                for channel_data in channel_list:
                    channel_info = parse_channel_info(channel_data)
                    future = executor.submit(process_channel, channel_info, category)
                    futures.append(future)
                
                # 收集结果
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        all_channels.append(result)
                        
        except Exception as e:
            print(f"处理分类 {category} 时出错: {e}")
            continue
    
    # 写入文件
    output_file = "output/migu.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(m3u_header)
        for channel in all_channels:
            f.write(channel)
    
    print(f"\nM3U文件生成完成: {output_file}")
    print(f"共生成 {len(all_channels)} 个频道")
    
    # 同时生成TXT文件
    generate_txt_file(all_channels)
    
    return all_channels

def generate_txt_file(channels):
    """生成TXT文件"""
    txt_file = "output/migu.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        for channel in channels:
            # 从M3U条目中提取频道名和URL
            lines = channel.strip().split('\n')
            if len(lines) >= 2:
                extinf = lines[0]
                url = lines[1]
                
                # 提取频道名（从逗号后面开始）
                if ',' in extinf:
                    channel_name = extinf.split(',')[-1].strip()
                    f.write(f"{channel_name},{url}\n")
    
    print(f"TXT文件生成完成: {txt_file}")

def main():
    """主函数"""
    print("开始爬取咪咕视频直播源...")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        channels = generate_m3u_file()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("=" * 50)
        print(f"爬取完成！耗时: {elapsed_time:.2f}秒")
        print(f"成功获取 {len(channels)} 个频道")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
