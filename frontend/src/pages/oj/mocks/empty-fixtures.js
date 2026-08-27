// Production-safe fixture surface. Vite aliases development fixtures to this
// module unless the explicit localhost frontend development switch is enabled.
export const MOCK_PROBLEMS = []
export const MOCK_CONTESTS = []
export const MOCK_ACM_RANK = []
export const MOCK_OI_RANK = []
export const MOCK_SUBMISSIONS = []

export function cloneFixtures (items = []) {
  return items.map(item => JSON.parse(JSON.stringify(item)))
}

export function filterMockProblems () {
  return []
}

export function filterMockContests () {
  return []
}
