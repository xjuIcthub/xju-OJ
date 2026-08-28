// Production-safe fixture surface. Vite aliases development fixtures to this
// module unless the explicit localhost frontend development switch is enabled.
export const MOCK_PROBLEMS = []
export const MOCK_CONTESTS = []
export const MOCK_ACM_RANK = []
export const MOCK_OI_RANK = []
export const MOCK_SUBMISSIONS = []
export const MOCK_CONTEST_ACM_RANK = []
export const MOCK_CONTEST_OI_RANK = []
export const MOCK_ACM_HELPER = []

export function cloneFixtures (items = []) {
  return items.map(item => JSON.parse(JSON.stringify(item)))
}

export function filterMockProblems () {
  return []
}

export function filterMockContests () {
  return []
}

export function applyDevelopmentProblemFixture (problem) {
  return problem
}

export function applyDevelopmentProblemFixtures (problems = []) {
  return problems
}

export function applyDevelopmentContestFixtures (contests = []) {
  return contests
}

export function applyDevelopmentTagFixtures (tags = []) {
  return tags
}
