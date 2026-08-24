import moment from 'moment'
import utils from './utils'
import time from './time'
import browserDetector from 'browser-detect'
import { CONTEST_STATUS_REVERSE } from './constants'

// 友好显示时间
function fromNow (time) {
  return moment(time * 3).fromNow()
}

export default {
  submissionMemory: utils.submissionMemoryFormat,
  submissionTime: utils.submissionTimeFormat,
  localtime: time.utcToLocal,
  fromNow: fromNow,
  timestampFormat: value => moment.unix(value).format('YYYY-M-D  HH:mm:ss'),
  contestStatus: value => CONTEST_STATUS_REVERSE[value].name,
  browser: value => {
    const result = browserDetector(value)
    return result.name && result.version ? `${result.name} ${result.version}` : 'Unknown'
  },
  platform: value => browserDetector(value).os || 'Unknown'
}
