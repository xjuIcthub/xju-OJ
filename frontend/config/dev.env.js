let date = require('moment')().format('YYYYMMDD')
let commit = process.env.GIT_COMMIT
if (!commit) {
  try {
    commit = require('child_process').execSync('git rev-parse HEAD 2>/dev/null').toString()
  } catch (e) {
    commit = 'unknown'
  }
}
commit = commit.toString().trim().slice(0, 7)
let version = `"${date}-${commit}"`

console.log(`current version is ${version}`)

module.exports = {
  NODE_ENV: '"development"',
  VERSION: version,
  USE_SENTRY: '0'
}
