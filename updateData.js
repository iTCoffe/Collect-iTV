import { dataList } from "./utils/fetchList.js"
import { appendFile, appendFileSync, copyFileSync, renameFileSync, writeFile } from "./utils/fileUtil.js"
import { updatePlaybackData } from "./utils/playback.js"
import { /* refreshToken as mrefreshToken, */ host, token, userId } from "./config.js"
import refreshToken from "./utils/refreshToken.js"
import { printGreen, printRed, printYellow } from "./utils/colorOut.js"
import { getDateString } from "./utils/time.js"

/**
 * @param {Number} hours -更新小时数 
 */
async function updateTV(hours) {

  const date = new Date()
  const start = date.getTime()
  let interfacePath = ""
  // 获取数据
  const datas = await dataList()
  printGreen("TV数据获取成功！")

  interfacePath = `${process.cwd()}/interface.txt.bak`
  // 创建写入空内容
  writeFile(interfacePath, "")

  if (!(hours % 24)) {
    // 每24小时刷新token
    if (userId != "" && token != "") {
      // if (mrefreshToken) {
      await refreshToken(userId, token) ? printGreen("token刷新成功") : printRed("token刷新失败")
      // } else {
      // printGreen(`跳过token刷新`)
      // }
    }
  }
  appendFile(interfacePath, `#EXTM3U x-tvg-url="\${replace}/playback.xml" catchup="append" catchup-source="?playbackbegin=\${(b)yyyyMMddHHmmss}&playbackend=\${(e)yyyyMMddHHmmss}"\n`)
  printYellow("开始更新TV...")
  // 回放
  const playbackFile = `${process.cwd()}/playback.xml.bak`
  writeFile(playbackFile,
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<tv generator-info-name="Tak" generator-info-url="${host}">\n`)

  // 分类列表
  for (let i = 0; i < datas.length; i++) {

    const data = datas[i].dataList
    // 写入节目
    for (let j = 0; j < data.length; j++) {

      await updatePlaybackData(data[j], playbackFile)

      // 写入节目
      appendFile(interfacePath, `#EXTINF:-1 tvg-id="${data[j].name}" tvg-name="${data[j].name}" tvg-logo="${data[j].pics.highResolutionH}" group-title="${datas[i].name}",${data[j].name}\n\${replace}/${data[j].pID}\n`)
      // printGreen(`    节目链接更新成功`)
    }
    printGreen(`分类###:${datas[i].name} 更新完成！`)
  }

  appendFileSync(playbackFile, `</tv>\n`)

  // 重命名
  renameFileSync(playbackFile, playbackFile.replace(".bak", ""))
  renameFileSync(interfacePath, interfacePath.replace(".bak", ""))
  printGreen("TV更新完成！")
  const end = Date.now()
  printYellow(`TV更新耗时: ${(end - start) / 1000}秒`)
}

/**
 * @param {Number} hours -更新小时数 
 */
async function updatePE(hours) {

  const date = new Date()
  const start = date.getTime()
  // 获取PE数据
  const datas = await fetch("http://v0-sc.miguvideo.com/vms-match/v6/staticcache/basic/match-list/normal-match-list/0/all/default/1/miguvideo").then(r => r.json())
  printGreen("PE数据获取成功！")
  // console.dir(datas, { depth: null })

  copyFileSync(`${process.cwd()}/interface.txt`, `${process.cwd()}/interface.txt.bak`, 0)
  const interfacePath = `${process.cwd()}/interface.txt.bak`

  printYellow("开始更新PE...")

  for (let i = 1; i < 4; i++) {
    // 日期
    const date = datas.body?.days[i]
    for (const data of datas.body?.matchList[date]) {
      let relativeDate = "昨天"
      const dateString = getDateString(new Date())
      if (date == dateString) {
        relativeDate = "今天"
      } else if (parseInt(date.substring(6)) > parseInt(dateString.substring(6))) {
        relativeDate = "明天"
      }

      let pkInfoTitle = data.pkInfoTitle
      if (data.confrontTeams) {
        pkInfoTitle = `${data.confrontTeams[0].name}VS${data.confrontTeams[1].name}`
      }
      // const peResult = await fetch(`http://app-sc.miguvideo.com/vms-match/v5/staticcache/basic/all-view-list/${data.mgdbId}/2/miguvideo`).then(r => r.json())
      const peResult = await fetch(`https://vms-sc.miguvideo.com/vms-match/v6/staticcache/basic/basic-data/${data.mgdbId}/miguvideo`).then(r => r.json())
      try {
        // 比赛已结束
        if (peResult.body.endTime < Date.now()) {
          const replayResult = await fetch(`http://app-sc.miguvideo.com/vms-match/v5/staticcache/basic/all-view-list/${data.mgdbId}/2/miguvideo`).then(r => r.json())
          let replayList = replayResult.body?.replayList
          if (replayList == null || replayList == undefined) {
            replayList = peResult.body.multiPlayList.replayList
          }
          if (replayList == null || replayList == undefined) {
            printYellow(`${data.mgdbId} ${pkInfoTitle} 无回放`)
            continue
          }
          for (const replay of replayList) {
            if (replay.name.match(/.*集锦|训练.*/) != null) {
              continue
            }
            if (replay.name.match(/.*回放|赛.*/) != null) {
              // 写入赛事
              appendFileSync(interfacePath, `#EXTINF:-1 tvg-id="${pkInfoTitle}" tvg-name="${pkInfoTitle}" tvg-logo="${data.competitionLogo}" group-title="体育-${relativeDate}",${data.competitionName} ${pkInfoTitle} ${replay.name} ${peResult.body.multiPlayList.preList[peResult.body.multiPlayList.preList.length - 1].startTimeStr.substring(11, 16)}\n\${replace}/${replay.pID}\n`)
            }
          }
          continue
        }
        // 比赛未结束
        const liveList = peResult.body.multiPlayList.liveList
        for (const live of liveList) {
          if (live.name.match(/.*集锦.*/) != null || live.startTimeStr == undefined) {
            continue
          }

          // 写入赛事
          appendFileSync(interfacePath, `#EXTINF:-1 tvg-id="${pkInfoTitle}" tvg-name="${pkInfoTitle}" tvg-logo="${data.competitionLogo}" group-title="体育-${relativeDate}",${data.competitionName} ${pkInfoTitle} ${live.name} ${live.startTimeStr.substring(11, 16)}\n\${replace}/${live.pID}\n`)
        }
      } catch (error) {
        printRed(`${data.mgdbId} ${pkInfoTitle} 更新失败`)
        printRed(error)
      }
    }
    printGreen(`日期 ${date} 更新完成！`)
  }

  // 重命名
  renameFileSync(interfacePath, interfacePath.replace(".bak", ""))
  printGreen("PE更新完成！")
  const end = Date.now()
  printYellow(`PE更新耗时: ${(end - start) / 1000}秒`)
}

/**
 * @param {Number} hours - 更新小时数
 */
async function update(hours) {
  await updateTV(hours)
  await updatePE(hours)
}

export default update
