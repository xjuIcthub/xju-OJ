import { createI18n } from 'vue-i18n'
import { m as enOJ } from './oj/en-US'
import { m as zhCNOJ } from './oj/zh-CN'
import { m as zhTWOJ } from './oj/zh-TW'
import { m as enAdmin } from './admin/en-US'
import { m as zhCNAdmin } from './admin/zh-CN'
import { m as zhTWAdmin } from './admin/zh-TW'

const languages = [
  { value: 'en-US', label: 'English' },
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' }
]
const messages = {
  'en-US': { m: { ...enOJ, ...enAdmin } },
  'zh-CN': { m: { ...zhCNOJ, ...zhCNAdmin } },
  'zh-TW': { m: { ...zhTWOJ, ...zhTWAdmin } }
}

export default createI18n({ legacy: false, globalInjection: true, locale: 'en-US', fallbackLocale: 'en-US', messages })
export { languages }
