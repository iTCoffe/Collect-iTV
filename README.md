# 使用方式

账号🐔了。~~只有标清..~~ 高清为主😅 gitee仓库被改私有了..

gitee ip被ban，仓库链接已失效

访问地址(可回看当天内容)

```
https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt

https://develop202.github.io/migu_video/interface.txt
```

网络环境差的话可以用这个(不一定稳定,其他加速网站也可以)

```
https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt
```

# 本地部署

> [!warning]
> 注意事项
>
> 1. 登录后使用不保证安全，请谨慎使用
> 1. 需要国内IP才可正常访问

## 配置

配置信息如下，默认本机和局域网可用

| 变量名    | 默认值 | 类型   | 介绍                                         |
| --------- | ------ | ------ | -------------------------------------------- |
| muserId   |        | string | 用户id，可在网页端登录获取                   |
| mtoken    |        | string | 用户token，可在网页端登录获取                |
| mport     | 1234   | number | 本地运行端口号                               |
| mhost     |        | string | 公网/自定义访问地址 格式<http://你的ip:1234> |
| mrateType | 3      | number | 画质 2:标清 3:高清 4:蓝光(需登录且有VIP)     |

## node

### 环境要求

需要 NodeJS 18+ 环境

### 安装

```shell
git clone git@github.com:develop202/migu_video.git
cd migu_video
```

### 运行

```shell
node app.js
```

若需要修改配置，可以使用以下命令
Mac/Linux:

```shell
mport=3000 mhost="http://localhost:3000" node app.js
```

Windows下使用git-bash等终端:

```shell
set mport=3000 && set mhost="http://localhost:3000" && node app.js
```

Windows下使用PowerShell等终端:

```shell
$Env:mport=3000; $Env:mhost="http://localhost:3000"; node app.js
```

## docker

初次使用，如有错误还请大佬指正。

### 安装

```shell
docker pull develop767/migu_video:latest
```

### 运行

```shell
docker run -p 1234:1234 --name migu_video develop767/migu_video
```

若需要修改配置，可以使用以下命令

```shell
docker run -p 3000:3000 -e mport=3000 -e mhost="http://localhost:3000" --name migu_video develop767/migu_video
```

### 构建

若需要手动构建镜像，可以使用以下命令

```shell
docker build -t migu_video .
```

# 免责声明

> [!important]
>
> 1. 本仓库仅供学习使用，请尊重版权，请勿利用此仓库从事商业行为及非法用途!
> 2. 使用本仓库的过程中可能会产生版权数据。对于这些版权数据，本仓库不拥有它们的所有权。为了避免侵权，使用者务必在 24小时内清除使用本仓库的过程中所产生的版权数据。
> 3. 由于使用本仓库产生的包括由于本协议或由于使用或无法使用本仓库而引起的任何性质的任何直接、间接、特殊、偶然或结果性损害（包括但不限于因商誉损失、停工、计算机故障或故障引起的损害赔偿，或任何及所有其他商业损害或损失）由使用者负责。
> 4. **禁止在违反当地法律法规的情况下使用本仓库。** 对于使用者在明知或不知当地法律法规不允许的情况下使用本仓库所造成的任何违法违规行为由使用者承担，本仓库不承担由此造成的任何直接、间接、特殊、偶然或结果性责任。
> 5. 如果官方平台觉得本仓库不妥，可联系本仓库更改或移除。
