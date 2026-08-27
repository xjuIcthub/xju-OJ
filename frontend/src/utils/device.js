import browserDetector from 'browser-detect'

const browserCache = new Map()

const readBrowser = (userAgent = '') => {
  const value = String(userAgent || '')
  if (!browserCache.has(value)) {
    browserCache.set(value, browserDetector(value))
  }
  return browserCache.get(value)
}

const versionOf = (userAgent, pattern) => {
  const match = String(userAgent || '').match(pattern)
  return match ? match[1] : ''
}

export const formatBrowser = (userAgent) => {
  const result = readBrowser(userAgent)
  return result.name && result.version ? `${result.name} ${result.version}` : 'Unknown'
}

export const formatPlatform = (userAgent) => {
  const value = String(userAgent || '')
  if (/Windows NT 10\.0/i.test(value)) return 'Windows 10/11'
  if (/Windows NT 6\.1/i.test(value)) return 'Windows 7'
  if (/Windows NT 6\.2/i.test(value)) return 'Windows 8'
  if (/Windows NT 6\.3/i.test(value)) return 'Windows 8.1'
  if (/(iPhone|iPad|iPod)/i.test(value)) return 'iOS'
  if (/Android/i.test(value)) {
    const version = versionOf(value, /Android\s+([\d.]+)/i)
    return version ? `Android ${version}` : 'Android'
  }
  if (/(Macintosh|Mac OS X)/i.test(value)) return 'macOS'
  if (/CrOS/i.test(value)) return 'ChromeOS'
  if (/Linux/i.test(value)) return 'Linux'
  return readBrowser(value).os || 'Unknown'
}

const formatClientHintPlatform = (platform, platformVersion) => {
  const value = String(platform || '')
  const version = String(platformVersion || '')
  if (value === 'Windows') {
    const major = Number.parseInt(version.split('.')[0], 10)
    // Chromium reports Windows 11 as platformVersion 13.x or newer. When the
    // hint is unavailable, keep the deliberately non-assertive fallback.
    if (Number.isFinite(major) && major >= 13) return 'Windows 11'
    if (Number.isFinite(major) && major >= 10) return 'Windows 10'
    return 'Windows 10/11'
  }
  if (value === 'macOS') return version ? `macOS ${version}` : 'macOS'
  if (value === 'Android') return version ? `Android ${version}` : 'Android'
  if (value === 'Chrome OS') return 'ChromeOS'
  if (value === 'Linux') return 'Linux'
  return value || ''
}

export const detectCurrentPlatform = async () => {
  if (typeof navigator === 'undefined' || !navigator.userAgentData) return ''
  try {
    const data = await navigator.userAgentData.getHighEntropyValues(['platformVersion'])
    return formatClientHintPlatform(data.platform || navigator.userAgentData.platform, data.platformVersion)
  } catch (_) {
    return ''
  }
}

