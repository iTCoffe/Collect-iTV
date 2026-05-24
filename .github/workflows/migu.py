import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 配置参数
thread_num = 10  # 线程数
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"

# 统一使用标准的咪咕客户端 H5/Android 伪装请求头
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://m.miguvideo.com",
    "Pragma": "no-cache",
    "Referer": "https://m.miguvideo.com/",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    "appCode": "miguvideo_default_h5",
    "appId": "miguvideo",
    "channel": "H5",
    "terminalId": "h5",
    "AppVersion": appVersion,
    "TerminalId": "android",
    "X-UP-CLIENT-CHANNEL-ID": appVersionID
}

lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE = {
    '热门': 'e7716fea6aa1483c80cfc10b7795fcb8', '体育': '7538163cdac044398cb292ecf75db4e0',
    '央视': '1ff892f2b5ab4a79be6e25b69d2f5d05', '卫视': '0847b3f6c08a4ca28f85ba5701268424',
    '地方': '855e9adc91b04ea18ef3f2dbd43f495b', '影视': '10b0d04cb23d4ac5945c4bc77c7ac44e',
    '新闻': 'c584f67ad63f4bc983c31de3a9be977c', '教育': 'af72267483d94275995a4498b2799ecd',
    '熊猫': 'e76e56e88fff4c11b0168f55e826445d', '综艺': '192a12edfef04b5eb616b878f031f32f',
    '少儿': 'fc2f5b8fd7db43ff88c4243e731ecede', '纪实': 'e1165138bdaa44b9a3138d74af6c6673'
}

All_Live = []
FLAG = 0

def format_date_ymd():
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"

def writefile(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def md5(text):
    md5_obj = hashlib.md5()
    md5_obj.update(text.encode('utf-8'))
    return md5_obj.hexdigest()

def getSaltAndSign(pid):
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {
        "salt": salt,
        "sign": sign,
        "timestamp": timestamp
    }

def get_content(pid):
    """
    精简重构：彻底抛弃 ApiPost 网页代理，直接向官方 playurl 接口发起请求
    """
    result = getSaltAndSign(pid)
    rateType = "3"
    
    # 构造请求参数
    params = {
        "sign": result["sign"],
        "rateType": rateType,
        "contId": pid,
        "timestamp": result["timestamp"],
        "salt": result["salt"]
    }
    
    url = "https://play.miguvideo.com/playurl/v1/play/playurl"
    
    # 直接请求官方接口，超时设为 10 秒防卡死
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    return resp.json()

def getddCalcu720p(url, pID):
    if "&puData=" not in url:
        return ""
    puData = url.split("&puData=")[1]
    keys = "cdabyzwxkl"
    ddCalcu = []
    for i in range(0, int(len(puData) / 2)):
        ddCalcu.append(puData[int(len(puData)) - i - 1])
        ddCalcu.append(puData[i])
        if i == 1:
            ddCalcu.append("v")
        if i == 2:
            ddCalcu.append(keys[int(format_date_ymd()[2])])
        if i == 3:
            ddCalcu.append(keys[int(pID[6])])
        if i == 4:
            ddCalcu.append("a")
    return f'{url}&ddCalcu={"".join(ddCalcu)}&sv=10004&ct=android'

def append_All_Live(live, flag, data):
    try:
        respData = get_content(data["pID"])
        
        # 增加安全防御：校验官方返回的 json 结构是否完整
        if not respData or "body" not in respData or "urlInfo" not in respData["body"]:
            print(f'频道 [{data["name"]}] 官方接口未返回有效播放流地址。')
            return
            
        raw_url = respData["body"]["urlInfo"].get("url", "")
        if not raw_url:
            print(f'频道 [{data["name"]}] URL 为空。')
            return

        playurl = getddCalcu720p(raw_url, data["pID"])
        if not playurl:
            return

        # 跟踪 302 重定向获取最终 HLS 链接
        z = 1
        while z <= 6:
            try:
                obj = requests.get(playurl, headers=headers, allow_redirects=False, timeout=5)
                location = obj.headers.get("Location", "")
                if not location:
                    break
                if location.startswith("http://hlsz") or "m3u8" in location:
                    playurl = location
                    break
                time.sleep(0.15)
                z += 1
            except Exception:
                break
                
        content = (
            f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" '
            f'tvg-logo="{data["pics"]["highResolutionH"]}" group-title="{live}",{data["name"]}\n'
            f'{playurl}\n'
        )
        
        All_Live[flag] = content
        print(f'频道 [{data["name"]}] 更新成功！')
    except Exception as e:
        print(f'频道 [{data["name"]}] 异步解析发生致命异常: {e}')

def update(live, url):
    global FLAG
    global All_Live
    global headers
    pool = ThreadPoolExecutor(thread_num)
    try:
        response = requests.get(url, headers=headers, timeout=15).json()
        dataList = response.get("body", {}).get("dataList", [])
        for flag, data in enumerate(dataList):
            All_Live.append("")
            pool.submit(append_All_Live, live, FLAG + flag, data)
    except Exception as e:
        print(f"分类 [{live}] 列表获取失败: {e}")
    finally:
        pool.shutdown(wait=True)
        if 'dataList' in locals():
            FLAG += len(dataList)

def main():
    # ==================== 1. 构建标准的 M3U 格式内容 ====================
    m3u_content = (
        '#EXTM3U x-tvg-url="https://itv.sspai.pp.ua/erw.xml.gz" catchup="append" '
        'catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
    )
    
    m3u_content += (
        '#EXTINF:-1 tvg-id="温馨提示" tvg-name="温馨提示" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/温馨提示.png" group-title="🦧温馨提示",温馨提示\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4n'
        '#EXTINF:-1 tvg-id="谨防诈骗" tvg-name="谨防诈骗" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/谨防诈骗.png" group-title="🦧温馨提示",谨防诈骗\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4n'
        '#EXTINF:-1 tvg-id="禁止蕉绿" tvg-name="禁止蕉绿" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/禁止蕉绿.png" group-title="🦧温馨提示",禁止蕉绿\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4n'
        '#EXTINF:-1 tvg-id="Cloudflare TV" tvg-name="Cloudflare TV" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/CloudflareTV.png" group-title="🦧温馨提示",Cloudflare TV\n'
        'https://cloudflare.tv/hls/live.m3u8n'
    )

    # ==================== 2. 开始抓取咪咕直播源 ====================
    for live in lives:
        print(f"分类 ----- [{live}] ----- 开始更新. . .")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)

    # 拼接数据
    for content in All_Live:
        if content:  
            m3u_content += content

    writefile("MiGu.m3u", m3u_content)
    print("✨ MiGu.m3u 生成完毕！")

    # ==================== 3. 规整并转换生成标准的 TXT 列表格式 ====================
    txt_lines = [
        "🦧温馨提示,#genre#",
        "温馨提示,https://icloud.ifanr.pp.ua/温馨提示.mp4",
        "谨防诈骗,https://icloud.ifanr.pp.ua/温馨提示.mp4",
        "禁止蕉绿,https://icloud.ifanr.pp.ua/温馨提示.mp4",
        "Cloudflare TV,https://cloudflare.tv/hls/live.m3u8"
    ]
    
    current_group = ""
    for content in All_Live:
        if not content:
            continue
        
        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                inf_line = lines[i]
                url_line = lines[i+1]
                
                try:
                    group = inf_line.split('group-title="')[1].split('"')[0]
                    name = inf_line.split(',')[-1].strip()
                    
                    if group != current_group:
                        current_group = group
                        txt_lines.append(f"{current_group},#genre#")
                    
                    txt_lines.append(f"{name},{url_line}")
                except Exception:
                    continue

    txt_content = "\n".join(txt_lines) + "\n"
    writefile("MiGu.txt", txt_content)
    print("✨ MiGu.txt 标准分类列表转换并生成完毕！")

if __name__ == "__main__":
    main()
