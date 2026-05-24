import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 配置参数
thread_num = 10
appVersion = "2600034600"
appVersionID = appVersion + "-99000-201600010010028"

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
    "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "terminalId": "h5"
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

# 修复：直接请求咪咕播放接口，移除 Apipost 代理
def get_content(pid):
    result = getSaltAndSign(pid)
    rateType = "3"
    url = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
    
    # 必须携带的请求头（从原 headers 中提取必要字段）
    req_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "AppVersion": appVersion,
        "TerminalId": "android",
        "X-UP-CLIENT-CHANNEL-ID": appVersionID,
        "User-Agent": headers["User-Agent"],
        "Origin": "https://m.miguvideo.com",
        "Referer": "https://m.miguvideo.com/",
        "appCode": "miguvideo_default_h5",
        "appId": "miguvideo",
        "channel": "H5"
    }
    
    resp = requests.get(url, headers=req_headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

# 修复：增加 puData 缺失的容错
def getddCalcu720p(url, pID):
    if "&puData=" not in url:
        return url  # 无法计算 ddCalcu 时返回原链接
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
    global All_Live
    try:
        respData = get_content(data["pID"])
        if "body" not in respData or "urlInfo" not in respData["body"] or "url" not in respData["body"]["urlInfo"]:
            raise ValueError("响应中未找到播放链接")
        playurl = respData["body"]["urlInfo"]["url"]
        playurl = getddCalcu720p(playurl, data["pID"])
        
        # 初始化重定向计数
        z = 1
        success = False
        if playurl:
            while z <= 6:
                try:
                    obj = requests.get(playurl, allow_redirects=False, timeout=10)
                    location = obj.headers.get("Location", "")
                    if location and location.startswith("http://hlsz"):
                        playurl = location
                        success = True
                        break
                except Exception:
                    pass
                time.sleep(0.15)
                z += 1
        else:
            print(f'频道 [{data["name"]}] 播放链接为空，跳过')
            return
        
        # 只有成功获取有效链接才写入
        if success:
            content = (
                f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" '
                f'tvg-logo="{data["pics"]["highResolutionH"]}" group-title="{live}",{data["name"]}\n'
                f'{playurl}\n'
            )
            All_Live[flag] = content
            print(f'频道 [{data["name"]}] 更新成功！')
        else:
            print(f'频道 [{data["name"]}] 更新失败！')
    except Exception as e:
        print(f'频道 [{data["name"]}] 更新失败：{e}')

def update(live, url):
    global FLAG, All_Live
    pool = ThreadPoolExecutor(thread_num)
    try:
        response = requests.get(url, headers=headers, timeout=10).json()
        dataList = response["body"]["dataList"]
    except Exception as e:
        print(f"分类 [{live}] 获取列表失败：{e}")
        return
    # 预先扩展列表长度
    for _ in range(len(dataList)):
        All_Live.append("")
    futures = []
    for idx, data in enumerate(dataList):
        futures.append(pool.submit(append_All_Live, live, FLAG + idx, data))
    # 等待所有任务完成
    for f in futures:
        f.result()
    pool.shutdown()
    FLAG += len(dataList)

def main():
    # 构建 M3U 头部
    m3u_content = (
        '#EXTM3U x-tvg-url="https://itv.sspai.pp.ua/erw.xml.gz" catchup="append" '
        'catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
    )
    # 添加提示频道
    tip_channels = [
        ("温馨提示", "https://icloud.ifanr.pp.ua/温馨提示.mp4"),
        ("谨防诈骗", "https://icloud.ifanr.pp.ua/温馨提示.mp4"),
        ("禁止蕉绿", "https://icloud.ifanr.pp.ua/温馨提示.mp4"),
        ("Cloudflare TV", "https://cloudflare.tv/hls/live.m3u8")
    ]
    for name, url in tip_channels:
        m3u_content += (
            f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
            f'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/{name}.png" group-title="🦧温馨提示",{name}\n'
            f'{url}\n'
        )
    
    # 抓取咪咕直播
    for live in lives:
        print(f"分类 ----- [{live}] ----- 开始更新...")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)
    
    # 拼接 M3U
    for content in All_Live:
        if content:
            m3u_content += content
    writefile("MiGu.m3u", m3u_content)
    print("✨ MiGu.m3u 生成完毕")
    
    # 生成 TXT 格式
    txt_lines = []
    # 温馨提示分类
    txt_lines.append("🦧温馨提示,#genre#")
    for name, url in tip_channels:
        txt_lines.append(f"{name},{url}")
    
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
    writefile("MiGu.txt", "\n".join(txt_lines) + "\n")
    print("✨ MiGu.txt 生成完毕")

if __name__ == "__main__":
    main()
