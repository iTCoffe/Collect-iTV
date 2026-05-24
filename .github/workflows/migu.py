import requests
import json
import time
import random
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ====================== 配置参数 ======================
thread_num = 10                # 线程数
appVersion = "2600034600"
appVersionID = f"{appVersion}-99000-201600010010028"

# 基础请求头（用于获取节目列表）
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

# 分类及对应的 categoryId
lives = ['热门', '央视', '卫视', '地方', '体育', '影视', '综艺', '少儿', '新闻', '教育', '熊猫', '纪实']
LIVE = {
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

All_Live = []          # 存储所有频道的 M3U 行
FLAG = 0               # 当前写入索引


# ====================== 辅助函数 ======================
def format_date_ymd():
    """返回 YYYYMMDD 格式字符串"""
    now = datetime.now()
    return f"{now.year}{now.month:02d}{now.day:02d}"


def writefile(path, content):
    """写入文件（UTF-8）"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def md5(text):
    """返回32位小写MD5"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def getSaltAndSign(pid):
    """生成请求所需的 salt, sign, timestamp"""
    timestamp = str(int(time.time() * 1000))
    random_num = random.randint(0, 999999)
    salt = f"{random_num:06d}25"
    suffix = "2cac4f2c6c3346a5b34e085725ef7e33migu" + salt[:4]
    app_t = timestamp + pid + appVersion[:8]
    sign = md5(md5(app_t) + suffix)
    return {"salt": salt, "sign": sign, "timestamp": timestamp}


def get_content(pid):
    """
    直接请求咪咕播放接口，返回 JSON
    带重试和详细日志
    """
    result = getSaltAndSign(pid)
    rateType = "3"
    url = (f"https://play.miguvideo.com/playurl/v1/play/playurl?"
           f"sign={result['sign']}&rateType={rateType}&contId={pid}"
           f"&timestamp={result['timestamp']}&salt={result['salt']}")

    # 必须携带的请求头（模拟 H5）
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
        "channel": "H5",
        "Cache-Control": "no-cache"
    }

    session = requests.Session()
    # 可选：先访问首页获取必要 Cookie
    try:
        session.get("https://m.miguvideo.com", headers=req_headers, timeout=5)
    except Exception:
        pass

    for attempt in range(3):  # 最多重试3次
        try:
            resp = session.get(url, headers=req_headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            print(f"[重试] {pid} 状态码 {resp.status_code}，第 {attempt+1} 次")
            time.sleep(1)
        except Exception as e:
            print(f"[重试] {pid} 请求异常: {e}，第 {attempt+1} 次")
            time.sleep(1)

    raise Exception(f"获取播放地址失败，pid={pid}")


def getddCalcu720p(url, pID):
    """
    计算 ddCalcu 参数（仿原逻辑）
    若 URL 不含 puData 则返回原链接
    """
    if not url or "&puData=" not in url:
        return url

    try:
        puData = url.split("&puData=")[1]
        keys = "cdabyzwxkl"
        ddCalcu = []
        length = len(puData)
        for i in range(0, length // 2):
            ddCalcu.append(puData[length - i - 1])
            ddCalcu.append(puData[i])
            if i == 1:
                ddCalcu.append("v")
            if i == 2:
                ddCalcu.append(keys[int(format_date_ymd()[2])])
            if i == 3:
                ddCalcu.append(keys[int(pID[6])])
            if i == 4:
                ddCalcu.append("a")
        return f"{url}&ddCalcu={''.join(ddCalcu)}&sv=10004&ct=android"
    except Exception as e:
        print(f"[警告] ddCalcu 计算失败: {e}")
        return url


def append_All_Live(live, flag, data):
    """单个频道的处理线程函数"""
    global All_Live
    channel_name = data.get("name", "未知频道")
    try:
        # 1. 获取播放地址
        respData = get_content(data["pID"])
        if "body" not in respData or "urlInfo" not in respData["body"]:
            raise ValueError("响应缺少 urlInfo")
        playurl = respData["body"]["urlInfo"].get("url")
        if not playurl:
            raise ValueError("播放链接为空")

        # 2. 添加 ddCalcu 参数
        playurl = getddCalcu720p(playurl, data["pID"])

        # 3. 重定向获取真实 hlsz 地址（最多6次）
        success = False
        for attempt in range(1, 7):
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

        if not success:
            raise Exception("未能获取到 hlsz 真实地址")

        # 4. 组装 M3U 行
        logo = data.get("pics", {}).get("highResolutionH", "")
        line = (f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" '
                f'tvg-logo="{logo}" group-title="{live}",{channel_name}\n{playurl}\n')
        All_Live[flag] = line
        print(f'✅ 频道 [{channel_name}] 更新成功')
    except Exception as e:
        print(f'❌ 频道 [{channel_name}] 更新失败: {type(e).__name__}: {e}')
        # 调试：打印完整堆栈（可选，取消注释以查看）
        # import traceback
        # traceback.print_exc()


def update(live, url):
    """处理一个分类下的所有频道"""
    global FLAG, All_Live
    print(f"\n📺 分类 【{live}】 开始更新...")

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        dataList = resp.json()["body"]["dataList"]
    except Exception as e:
        print(f"❌ 分类 [{live}] 获取频道列表失败: {e}")
        return

    # 预先扩充 All_Live 列表
    start_idx = FLAG
    for _ in dataList:
        All_Live.append("")

    # 提交线程任务
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = {}
        for idx, data in enumerate(dataList):
            future = executor.submit(append_All_Live, live, start_idx + idx, data)
            futures[future] = (live, data.get("name", "未知"))

        # 等待所有完成
        for future in as_completed(futures):
            # 可在此处理完成后的回调，目前无需额外操作
            pass

    FLAG += len(dataList)
    print(f"📺 分类 【{live}】 处理完毕，共 {len(dataList)} 个频道")


# ====================== 主函数 ======================
def main():
    # 1. 构建 M3U 头部和温馨提示频道
    m3u_content = (
        '#EXTM3U x-tvg-url="https://itv.sspai.pp.ua/erw.xml.gz" catchup="append" '
        'catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
    )

    tip_channels = [
        ("温馨提示", "https://icloud.ifanr.pp.ua/温馨提示.mp4",
         "https://logo.jsdelivr.dpdns.org/tv/温馨提示.png"),
        ("谨防诈骗", "https://icloud.ifanr.pp.ua/温馨提示.mp4",
         "https://logo.jsdelivr.dpdns.org/tv/谨防诈骗.png"),
        ("禁止蕉绿", "https://icloud.ifanr.pp.ua/温馨提示.mp4",
         "https://logo.jsdelivr.dpdns.org/tv/禁止蕉绿.png"),
        ("Cloudflare TV", "https://cloudflare.tv/hls/live.m3u8",
         "https://logo.jsdelivr.dpdns.org/tv/CloudflareTV.png"),
    ]
    for name, stream_url, logo in tip_channels:
        m3u_content += (
            f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" '
            f'tvg-logo="{logo}" group-title="🦧温馨提示",{name}\n{stream_url}\n'
        )

    # 2. 抓取所有咪咕直播频道
    for live in lives:
        category_id = LIVE.get(live)
        if not category_id:
            print(f"⚠️ 未知分类: {live}，跳过")
            continue
        url = f"https://program-sc.miguvideo.com/live/v2/tv-data/{category_id}"
        update(live, url)

    # 3. 拼接完整 M3U 内容并写入文件
    for line in All_Live:
        if line:
            m3u_content += line
    writefile("MiGu.m3u", m3u_content)
    print("\n✨ MiGu.m3u 生成完毕")

    # 4. 生成 TXT 格式（分类列表）
    txt_lines = []
    # 添加温馨提示分类
    txt_lines.append("🦧温馨提示,#genre#")
    for name, stream_url, _ in tip_channels:
        txt_lines.append(f"{name},{stream_url}")

    current_group = ""
    for line in All_Live:
        if not line:
            continue
        # 每一条有效记录包含两行：EXTINF 行和 URL 行
        lines = [l.strip() for l in line.strip().split('\n') if l.strip()]
        for i in range(0, len(lines), 2):
            if i + 1 >= len(lines):
                break
            inf_line = lines[i]
            url_line = lines[i + 1]
            try:
                group = inf_line.split('group-title="')[1].split('"')[0]
                name = inf_line.split(',')[-1].strip()
                if group != current_group:
                    current_group = group
                    txt_lines.append(f"{current_group},#genre#")
                txt_lines.append(f"{name},{url_line}")
            except Exception as e:
                print(f"[TXT转换警告] 解析失败: {e}")

    writefile("MiGu.txt", "\n".join(txt_lines) + "\n")
    print("✨ MiGu.txt 生成完毕")


if __name__ == "__main__":
    main()
