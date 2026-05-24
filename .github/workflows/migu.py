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
    """格式化日期为「年+补0月+补0日」字符串"""
    current_date = datetime.now()
    return f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"

def writefile(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def md5(text):
    """MD5加密：返回32位小写结果"""
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
    URL = f"https://play.miguvideo.com/playurl/v1/play/playurl?sign={result['sign']}&rateType={rateType}&contId={pid}&timestamp={result['timestamp']}&salt={result['salt']}"
    params = URL.split("?")[1].split("&")
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
    body = json.dumps(body, separators=(",", ":"))
    url = "https://workspace.apipost.net/proxy/v2/http"
    resp = requests.post(url, headers=_headers, data=body).json()
    return json.loads(resp["data"]["data"]["response"]["body"])

def getddCalcu720p(url, pID):
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
        playurl = getddCalcu720p(respData["body"]["urlInfo"]["url"], data["pID"])

        if playurl != "":
            z = 1
            while z <= 6:
                obj = requests.get(playurl, allow_redirects=False)
                location = obj.headers.get("Location", "")
                if not location:
                    continue
                if location.startswith("http://hlsz"):
                    playurl = location
                    break
                if z <= 6:
                    time.sleep(0.15)
                z += 1
                
        # 确保咪咕抓取出的频道带有规范换行 \n
        content = (
            f'#EXTINF:-1 tvg-id="{data["name"]}" tvg-name="{data["name"]}" '
            f'tvg-logo="{data["pics"]["highResolutionH"]}" group-title="{live}",{data["name"]}\n'
            f'{playurl}\n'
        )
        if z == 7:
            print(f'频道 [{data["name"]}] 更新失败！')
        else:
            All_Live[flag] = content
            print(f'频道 [{data["name"]}] 更新成功！')
    except Exception as e:
        print(f'频道 [{data["name"]}] 更新失败！')
        print(f"ERROR:{e}")

def update(live, url):
    global FLAG
    global All_Live
    global headers
    pool = ThreadPoolExecutor(thread_num)
    response = requests.get(url, headers=headers).json()
    dataList = response["body"]["dataList"]
    for flag, data in enumerate(dataList):
        All_Live.append("")
        pool.submit(append_All_Live, live, FLAG + flag, data)
    pool.shutdown()
    FLAG += len(dataList)

def main():
    # ==================== 1. 构建标准的 M3U 格式内容 ====================
    # 彻底检查：全部去除末尾误写的英文字母 n，统一采用系统的 \n 硬换行
    m3u_content = (
        '#EXTM3U x-tvg-url="https://itv.sspai.pp.ua/erw.xml.gz" catchup="append" '
        'catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
    )
    
    # 写入 温馨提示
    m3u_content += (
        '#EXTINF:-1 tvg-id="温馨提示" tvg-name="温馨提示" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/温馨提示.png" group-title="🦧温馨提示",温馨提示\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4\n'
    )
    # 写入 谨防诈骗
    m3u_content += (
        '#EXTINF:-1 tvg-id="谨防诈骗" tvg-name="谨防诈骗" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/谨防诈骗.png" group-title="🦧温馨提示",谨防诈骗\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4\n'
    )
    # 写入 禁止蕉绿
    m3u_content += (
        '#EXTINF:-1 tvg-id="禁止蕉绿" tvg-name="禁止蕉绿" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/禁止蕉绿.png" group-title="🦧温馨提示",禁止蕉绿\n'
        'https://icloud.ifanr.pp.ua/温馨提示.mp4\n'
    )
    # 写入 Cloudflare TV
    m3u_content += (
        '#EXTINF:-1 tvg-id="Cloudflare TV" tvg-name="Cloudflare TV" '
        'tvg-logo="https://logo.jsdelivr.dpdns.org/tv/CloudflareTV.png" group-title="🦧温馨提示",Cloudflare TV\n'
        'https://cloudflare.tv/hls/live.m3u8\n'
    )

    # ==================== 2. 开始抓取咪咕直播源 ====================
    for live in lives:
        print(f"分类 ----- [{live}] ----- 开始更新. . .")
        url = f'https://program-sc.miguvideo.com/live/v2/tv-data/{LIVE[live]}'
        update(live, url)

    # 拼接爬回来的咪咕源数据
    for content in All_Live:
        if content:  
            m3u_content += content

    # 写入最终的 MiGu.m3u 列表文件
    writefile("MiGu.m3u", m3u_content)
    print("✨ MiGu.m3u 生成完毕（结构已彻底规整）！")


    # ==================== 3. 规整并转换生成标准的 TXT 列表格式 ====================
    txt_lines = []
    
    # 写入 TXT 的温馨提示专属分类
    txt_lines.append("🦧温馨提示,#genre#")
    txt_lines.append("温馨提示,https://icloud.ifanr.pp.ua/温馨提示.mp4")
    txt_lines.append("谨防诈骗,https://icloud.ifanr.pp.ua/温馨提示.mp4")
    txt_lines.append("禁止蕉绿,https://icloud.ifanr.pp.ua/温馨提示.mp4")
    txt_lines.append("Cloudflare TV,https://cloudflare.tv/hls/live.m3u8")
    
    # 过滤解析 All_Live 并将其实时格式化输出
    current_group = ""
    for content in All_Live:
        if not content:
            continue
        
        # 将每一组的 #EXTINF 与 URL 解离出来
        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                inf_line = lines[i]
                url_line = lines[i+1]
                
                try:
                    # 动态清洗捕获 group-title 与 频道名字
                    group = inf_line.split('group-title="')[1].split('"')[0]
                    name = inf_line.split(',')[-1].strip()
                    
                    # 切换分类时，优雅地增加 TXT 的分类标签
                    if group != current_group:
                        current_group = group
                        txt_lines.append(f"{current_group},#genre#")
                    
                    # 严密录入: 名字,链接
                    txt_lines.append(f"{name},{url_line}")
                except Exception:
                    continue

    # 封包写入 MiGu.txt 格式
    txt_content = "\n".join(txt_lines) + "\n"
    writefile("MiGu.txt", txt_content)
    print("✨ MiGu.txt 标准分类列表转换并生成完毕！")

if __name__ == "__main__":
    main()
