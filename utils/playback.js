import { getDateString, getDateTimeString } from "./time.js"
import { appendFileSync } from "./fileUtil.js"
import { cntvNames } from "./datas.js"


async function getPlaybackData(programId) {
  const date = new Date()
  const today = getDateString(date)
  const resp = await fetch(`https://program-sc.miguvideo.com/live/v2/tv-programs-data/${programId}/${today}`).then(r => r.json())
  return resp.body?.program[0]?.content
}

async function updatePlaybackDataByMigu(program, filePath) {
  // 今日节目数据
  const playbackData = await getPlaybackData(program.pID)
  if (!playbackData) {
    return false
  }
  // 写入频道信息
  appendFileSync(filePath,
    `    <channel id="${program.name}">\n` +
    `        <display-name lang="zh">${program.name}</display-name>\n` +
    `    </channel>\n`
  )

  // 写入节目信息
  for (let i = 0; i < playbackData.length; i++) {
    // 特殊字符转义
    const contName = playbackData[i].contName.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\"", "&quot;").replaceAll("'", "&apos;");

    appendFileSync(filePath,
      `    <programme channel="${program.name}" start="${getDateTimeString(new Date(playbackData[i].startTime))} +0800" stop="${getDateTimeString(new Date(playbackData[i].endTime))} +0800">\n` +
      `        <title lang="zh">${contName}</title>\n` +
      `    </programme>\n`
    )
  }
  return true
}

async function updatePlaybackDataByCntv(program, filePath) {
  // 今日节目数据
  const date = new Date()
  const today = getDateString(date)
  const cntvName = cntvNames[program.name]
  const resp = await fetch(`https://api.cntv.cn/epg/epginfo3?serviceId=shiyi&d=${today}&c=${cntvName}`).then(r => r.json())

  const playbackData = resp[cntvName]?.program
  if (!playbackData) {
    return false
  }
  // 写入频道信息
  appendFileSync(filePath,
    `    <channel id="${program.name}">\n` +
    `        <display-name lang="zh">${program.name}</display-name>\n` +
    `    </channel>\n`
  )

  // 写入节目信息
  for (let i = 0; i < playbackData.length; i++) {
    // 特殊字符转义
    const contName = playbackData[i].t.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\"", "&quot;").replaceAll("'", "&apos;");

    appendFileSync(filePath,
      `    <programme channel="${program.name}" start="${getDateTimeString(new Date(playbackData[i].st * 1000))} +0800" stop="${getDateTimeString(new Date(playbackData[i].et * 1000))} +0800">\n` +
      `        <title lang="zh">${contName}</title>\n` +
      `    </programme>\n`
    )
  }
  return true
}

async function updatePlaybackData(program, filePath) {
  if (cntvNames[program.name]) {
    return updatePlaybackDataByCntv(program, filePath)
  }
  return updatePlaybackDataByMigu(program, filePath)

}
export { updatePlaybackData }

