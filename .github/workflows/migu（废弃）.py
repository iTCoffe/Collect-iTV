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

# 用于获取分类列表的请求头
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

# 分类映射
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

All_Live = []   # 存储所有频道的 M3U 行
FLAG = 0        # 当前写入索引


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
    """通过 Apipost 代理获取播放地址（保留原始可用方式）"""
    # Apipost 代理专用请求头（保持原样）
    _headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "apipost-client-id": "465aea51-4548-495a-8709-7e532dbe3703",
        "apipost-language": "zh-cn",
        "apipost-machine": "3a214a07786002",
        "apipost-platform": "Win",
        "apipost-terminal": "web",
        "apipost-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InVzZXJfaWQiOjM5NDY2NDM3MTIyMzAwMzEzNywidGltZSI6MTc2NTYzMjU2NSwidXVpZCI6ImJlNDJjOTMxLWQ4MjctMTFmMC1hNThiLTUyZTY1ODM4NDNhOSJ9fQ.QU0RXa0e-yB-fwJNjYt_OnyM6RteY3L1BaUWqCrdAB4",
        "apipost-version": "8.2.6",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "apipost-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InVzZXJfaWQiOjM5NDY2NDM3MTIyMzAwMzEzNywidGltZSI6MTc2NTYzMjU2NSwidXVpZCI6ImJlNDJjOTMxLWQ4MjctMTFmMC1hNThiLTUyZTY1ODM4NDNhOSJ9fQ.QU0RXa0e-yB-fwJNjYt_OnyM6RteY3L1BaUWqCrdAB4; SERVERID=236fe4f21bf23223c449a2ac2dc20aa4|1765632725|1765632691; SERVERCORSID=236fe4f21bf23223c449a2ac2dc20aa4|1765632725|1765632691",
        "Referer": "https://workspace.apipost.net/57a21612a051000/apis",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    result = getSaltAndSign(pid)
    rateType = "3"
    URL = (f"https://play.miguvideo.com/playurl/v1/play/playurl?"
           f"sign={result['sign']}&rateType={rateType}&contId={pid}"
           f"&timestamp={result['timestamp']}&salt={result['salt']}")
    params = URL.split("?")[1].split("&")

    # 构建 Apipost 代理请求体（与原代码完全相同）
    body = {
        "option": {
            "scene": "http_request",
            "lang": "zh-cn",
            "globals": {},
            "project": {
                "request": {
                    "header": {
                        "parameter": [
                            {"key": "Accept", "value": "*/*", "is_checked": 1, "field_type": "String", "is_system": 1},
                            {"key": "Accept-Encoding", "value": "gzip, deflate, br", "is_checked": 1, "field_type": "String", "is_system": 1},
                            {"key": "User-Agent", "value": "PostmanRuntime-ApipostRuntime/1.1.0", "is_checked": 1, "field_type": "String", "is_system": 1},
                            {"key": "Connection", "value": "keep-alive", "is_checked": 1, "field_type": "String", "is_system": 1}
                        ]
                    },
                    "query": {"parameter": []},
                    "body": {"parameter": []},
                    "cookie": {"parameter": []},
                    "auth": {"type": "noauth"},
                    "pre_tasks": [],
                    "post_tasks": []
                }
            },
            "env": {
                "env_id": "1",
                "env_name": "默认环境",
                "env_pre_url": "",
                "env_pre_urls": {
                    "1": {"server_id": "1", "name": "默认服务", "sort": 1000, "uri": ""},
                    "default": {"server_id": "1", "name": "默认服务", "sort": 1000, "uri": ""}
                },
                "environment": {}
            },
            "cookies": {"switch": 1, "data": []},
            "system_configs": {
                "send_timeout": 0,
                "auto_redirect": -1,
                "max_redirect_time": 5,
                "auto_gen_mock_url": -1,
                "request_param_auto_json": -1,
                "proxy": {
                    "type": 2, "envfirst": 1, "bypass": [], "protocols": ["http"],
                    "auth": {"authenticate": -1, "host": "", "username": "", "password": ""}
                },
                "ca_cert": {"open": -1, "path": "", "base64": ""},
                "client_cert": {}
            },
            "custom_functions": {},
            "collection": [
                {
                    "target_id": "3c5fd6a9786002",
                    "target_type": "api",
                    "parent_id": "0",
                    "name": "MIGU",
                    "request": {
                        "auth": {"type": "inherit"},
                        "body": {"mode": "None", "parameter": [], "raw": "", "raw_parameter": [], "raw_schema": {"type": "object"}, "binary": None},
                        "pre_tasks": [],
                        "post_tasks": [],
                        "header": {
                            "parameter": [
                                {"description": "", "field_type": "string", "is_checked": 1, "key": " AppVersion", "value": "2600034600", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c60653273e0b3"},
                                {"description": "", "field_type": "string", "is_checked": 1, "key": "TerminalId", "value": "android", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c6075c1f3e0e1"},
                                {"description": "", "field_type": "string", "is_checked": 1, "key": "X-UP-CLIENT-CHANNEL-ID", "value": "2600034600-99000-201600010010028", "not_None": 1, "schema": {"type": "string"}, "param_id": "3c60858bb3e10c"}
                            ]
                        },
                        "query": {
                            "parameter": [
                                {"param_id": "3c5fd74233e004", "field_type": "string", "is_checked": 1, "key": "sign", "not_None": 1, "value": params[0].split("=")[1], "description": ""},
                                {"param_id": "3c6022f433e030", "field_type": "string", "is_checked": 1, "key": "rateType", "not_None": 1, "value": params[1].split("=")[1], "description": ""},
                                {"param_id": "3c60354133e05b", "field_type": "string", "is_checked": 1, "key": "contId", "not_None": 1, "value": params[2].split("=")[1], "description": ""},
                                {"param_id": "3c605e4bf860b1", "field_type": "String", "is_checked": 1, "key": "timestamp", "not_None": 1, "value": params[3].split("=")[1], "description": ""},
                                {"param_id": "3c605e4c3860b2", "field_type": "String", "is_checked": 1, "key": "salt", "not_None": 1, "value": params[4].split("=")[1], "description": ""}
                            ],
                            "query_add_equal": 1
                        },
                        "cookie": {"parameter": [], "cookie_encode": 1},
                        "restful": {"parameter": []},
                        "tabs_default_active_key": "query"
                    },
                    "parents": [],
                    "method": "POST",
                    "protocol": "http/1.1",
                    "url": URL,
                    "pre_url": ""
                }
            ],
            "database_configs": {}
        },
        "test_events": [
            {"type": "api", "data": {"target_id": "3c5fd6a9786002", "project_id": "57a21612a051000", "parent_id": "0", "target_type": "api"}}
        ]
    }

    body_json = json.dumps(body, separators=(",", ":"))
    proxy_url = "https://workspace.apipost.net/proxy/v2/http"

    # 增加重试机制
    for retry in range(3):
        try:
            resp = requests.post(proxy_url, headers=_headers, data=body_json, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            # 解析 Apipost 返回的数据结构
            response_body = json.loads(result["data"]["data"]["response"]["body"])
            return response_body
        except Exception as e:
            if retry == 2:
                raise Exception(f"获取播放地址失败（重试3次）: {e}")
            time.sleep(1)


def getddCalcu720p(url, pID):
    """
    计算 ddCalcu 参数（修复：若缺少 puData 则直接返回原链接）
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
                # 防止 pID 长度不足导致索引越界
                idx = int(pID[6]) if len(pID) > 6 else 0
                ddCalcu.append(keys[idx % len(keys)])
            if i == 4:
                ddCalcu.append("a")
        return f"{url}&ddCalcu={''.join(ddCalcu)}&sv=10004&ct=android"
    except Exception:
        # 任何解析错误都返回原链接
        return url


def append_All_Live(live, flag, data):
    """单个频道的处理线程函数（修复重定向循环和 urlInfo 空值）"""
    global All_Live
    channel_name = data.get("name", "未知频道")
    # 初始化状态变量
    success = False
    playurl = ""

    try:
        # 1. 通过代理获取播放地址
        respData = get_content(data["pID"])
        if "body" not in respData:
            raise ValueError("响应缺少 body 字段")
        url_info = respData["body"].get("urlInfo")
        if not url_info:
            raise ValueError("响应缺少 urlInfo 或值为空")
        playurl = url_info.get("url", "")
        if not playurl:
            raise ValueError("播放链接为空")

        # 2. 添加 ddCalcu 参数
        playurl = getddCalcu720p(playurl, data["pID"])

        # 3. 重定向获取真实 hlsz 地址（修复：正确更新 playurl 以跟随重定向）
        max_redirects = 6
        for attempt in range(max_redirects):
            try:
                obj = requests.get(playurl, allow_redirects=False, timeout=10)
                location = obj.headers.get("Location", "")
                if location:
                    playurl = location  # 更新为重定向地址
                    if location.startswith("http://hlsz"):
                        success = True
                        break
                else:
                    # 没有 Location 头，检查状态码
                    if obj.status_code == 200:
                        success = True
                        break
                    else:
                        # 非重定向状态码且无 Location，视为失败
                        raise Exception(f"HTTP {obj.status_code}")
            except requests.RequestException as e:
                if attempt == max_redirects - 1:
                    raise Exception(f"重定向请求异常: {e}")
            time.sleep(0.15)

        if not success:
            raise Exception("未能获取到有效的 hlsz 地址或最终可播放地址")

        # 4. 组装 M3U 行
        logo = data.get("pics", {}).get("highResolutionH", "")
        line = (f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" '
                f'tvg-logo="{logo}" group-title="{live}",{channel_name}\n{playurl}\n')
        All_Live[flag] = line
        print(f'✅ 频道 [{channel_name}] 更新成功')
    except Exception as e:
        print(f'❌ 频道 [{channel_name}] 更新失败: {type(e).__name__}: {e}')
        # 失败时留空，不写入内容


def update(live, url):
    """处理一个分类下的所有频道"""
    global FLAG, All_Live
    print(f"\n📺 分类 【{live}】 开始更新...")

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        dataList = resp.json()["body"]["dataList"]
    except Exception as e:
        print(f"❌ 分类 [{live}] 获取频道列表失败: {e}")
        return

    # 预先扩展 All_Live 列表
    start_idx = FLAG
    for _ in dataList:
        All_Live.append("")

    # 使用线程池处理，并等待所有完成
    with ThreadPoolExecutor(max_workers=thread_num) as executor:
        futures = []
        for idx, data in enumerate(dataList):
            futures.append(executor.submit(append_All_Live, live, start_idx + idx, data))
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"线程任务异常: {e}")

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
