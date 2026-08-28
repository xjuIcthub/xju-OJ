// Lightweight local fixtures keep the public pages useful when the development
// backend has no seeded rows yet. Real API responses always take precedence.
function isoFromNow (days, hour = 10) {
  const date = new Date(Date.now() + days * 24 * 60 * 60 * 1000)
  date.setHours(hour, 0, 0, 0)
  return date.toISOString()
}

export const MOCK_PROBLEMS = [
  {
    _id: '1001',
    title: 'Integer Addition',
    difficulty: 'Low',
    rule_type: 'ACM',
    submission_number: 428,
    accepted_number: 391,
    tags: ['math', 'beginner'],
    visible: true,
    my_status: null,
    id: '1001',
    description: '<p>Read two integers <code>a</code> and <code>b</code>, then print their sum.</p>',
    input_description: '<p>The only line contains two integers <code>a</code> and <code>b</code>.</p>',
    output_description: '<p>Print <code>a + b</code> on one line.</p>',
    samples: [{ input: '2 3', output: '5' }],
    hint: 'Use a 64-bit integer type if your language needs it.',
    source: 'XJU-OJ problem set',
    test_case_id: 'mock-1001-integer-addition',
    test_case_score: [{ input_name: '1.in', output_name: '1.out', score: 0 }],
    time_limit: 1000,
    memory_limit: 128,
    io_mode: { io_mode: 'Standard IO' },
    created_by: { username: 'XJU-ICTHub' },
    languages: ['C++', 'Python3', 'Java'],
    template: {
      'C++': '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    long long a, b;\n    cin >> a >> b;\n    cout << a + b << "\\n";\n    return 0;\n}',
      Python3: 'a, b = map(int, input().split())\nprint(a + b)',
      Java: 'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        System.out.println(in.nextLong() + in.nextLong());\n    }\n}'
    },
    statistic_info: { '0': 391, '-1': 37 }
  },
  {
    _id: '1002',
    title: 'Decimal Addition',
    difficulty: 'Mid',
    rule_type: 'ACM',
    submission_number: 276,
    accepted_number: 218,
    tags: ['math', 'precision'],
    visible: true,
    my_status: null,
    id: '1002',
    description: '<p>Read two decimal numbers and print their sum with exactly two digits after the decimal point.</p>',
    input_description: '<p>The only line contains two real numbers <code>a</code> and <code>b</code>.</p>',
    output_description: '<p>Print the sum of <code>a</code> and <code>b</code>, rounded to two decimal places.</p>',
    samples: [{ input: '1.25 2.50', output: '3.75' }],
    hint: 'Use fixed-point formatting and a small epsilon when comparing floating-point values.',
    source: 'XJU-OJ problem set',
    test_case_id: 'mock-1002-decimal-addition',
    test_case_score: [{ input_name: '1.in', output_name: '1.out', score: 0 }],
    time_limit: 1000,
    memory_limit: 128,
    io_mode: { io_mode: 'Standard IO' },
    created_by: { username: 'XJU-ICTHub' },
    languages: ['C++', 'Python3', 'Java'],
    template: {
      'C++': '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    double a, b;\n    cin >> a >> b;\n    cout << fixed << setprecision(2) << a + b << "\\n";\n    return 0;\n}',
      Python3: 'a, b = map(float, input().split())\nprint(f"{a + b:.2f}")',
      Java: 'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner in = new Scanner(System.in);\n        System.out.printf("%.2f%n", in.nextDouble() + in.nextDouble());\n    }\n}'
    },
    statistic_info: { '0': 218, '-1': 58 }
  },
]

export const MOCK_CONTESTS = [
  {
    id: 101,
    title: 'Integer Addition Practice',
    start_time: isoFromNow(2, 19),
    end_time: isoFromNow(2, 21),
    rule_type: 'ACM',
    contest_type: 'Public',
    status: '1',
    problem_ids: ['1001', '1002'],
    problems: ['1001', '1002'],
    description: '<h3>Contest overview</h3><p>Practice the two official XJU-OJ problem-set entries covering integer and decimal addition.</p>',
    now: new Date().toISOString(),
    created_by: { id: 'mock-admin', username: 'XJU-ICTHub' },
    real_time_rank: true
  },
  {
    id: 102,
    title: 'Decimal Addition Challenge',
    start_time: isoFromNow(7, 14),
    end_time: isoFromNow(7, 17),
    rule_type: 'OI',
    contest_type: 'Public',
    status: '1',
    problem_ids: ['1001', '1002'],
    problems: ['1001', '1002'],
    description: '<h3>Contest overview</h3><p>This challenge revisits both official problem-set entries with attention to numeric formatting and precision.</p>',
    now: new Date().toISOString(),
    created_by: { id: 'mock-admin', username: 'XJU-ICTHub' },
    real_time_rank: true
  }
]

export const MOCK_ACM_RANK = [
  { user: { username: 'alice' }, mood: 'Keep solving', accepted_number: 128, submission_number: 141 },
  { user: { username: 'bob' }, mood: 'On a streak', accepted_number: 117, submission_number: 136 },
  { user: { username: 'charlie' }, mood: 'First blood hunter', accepted_number: 103, submission_number: 129 },
  { user: { username: 'diana' }, mood: 'Learn by doing', accepted_number: 96, submission_number: 121 },
  { user: { username: 'evan' }, mood: 'Never give up', accepted_number: 84, submission_number: 112 },
  { user: { username: 'frank' }, mood: 'Weekend coder', accepted_number: 73, submission_number: 98 }
]

export const MOCK_OI_RANK = [
  { user: { username: 'alice' }, mood: 'Keep solving', total_score: 986, accepted_number: 18, submission_number: 20 },
  { user: { username: 'charlie' }, mood: 'First blood hunter', total_score: 941, accepted_number: 17, submission_number: 21 },
  { user: { username: 'diana' }, mood: 'Learn by doing', total_score: 905, accepted_number: 16, submission_number: 20 },
  { user: { username: 'bob' }, mood: 'On a streak', total_score: 872, accepted_number: 15, submission_number: 22 },
  { user: { username: 'evan' }, mood: 'Never give up', total_score: 816, accepted_number: 14, submission_number: 24 },
  { user: { username: 'frank' }, mood: 'Weekend coder', total_score: 768, accepted_number: 13, submission_number: 23 }
]

export const MOCK_CONTEST_ACM_RANK = [
  {
    id: 1,
    user: { id: 11, username: 'alice', real_name: 'Alice Chen' },
    accepted_number: 2,
    submission_number: 3,
    total_time: 1560,
    submission_info: {
      1001: { is_ac: true, ac_time: 420, error_number: 0, is_first_ac: true },
      1002: { is_ac: true, ac_time: 840, error_number: 1, is_first_ac: false }
    }
  },
  {
    id: 2,
    user: { id: 12, username: 'bob', real_name: 'Bob Li' },
    accepted_number: 2,
    submission_number: 4,
    total_time: 2460,
    submission_info: {
      1001: { is_ac: true, ac_time: 610, error_number: 1, is_first_ac: false },
      1002: { is_ac: true, ac_time: 1250, error_number: 1, is_first_ac: false }
    }
  },
  {
    id: 3,
    user: { id: 13, username: 'charlie', real_name: 'Charlie Wang' },
    accepted_number: 1,
    submission_number: 2,
    total_time: 930,
    submission_info: {
      1001: { is_ac: true, ac_time: 930, error_number: 0, is_first_ac: false },
      1002: { is_ac: false, ac_time: 0, error_number: 1, is_first_ac: false }
    }
  },
  {
    id: 4,
    user: { id: 14, username: 'diana', real_name: 'Diana Zhao' },
    accepted_number: 1,
    submission_number: 3,
    total_time: 1740,
    submission_info: {
      1001: { is_ac: false, ac_time: 0, error_number: 2, is_first_ac: false },
      1002: { is_ac: true, ac_time: 1140, error_number: 1, is_first_ac: true }
    }
  },
  {
    id: 5,
    user: { id: 15, username: 'evan', real_name: 'Evan Sun' },
    accepted_number: 0,
    submission_number: 2,
    total_time: 0,
    submission_info: {
      1001: { is_ac: false, ac_time: 0, error_number: 1, is_first_ac: false },
      1002: { is_ac: false, ac_time: 0, error_number: 1, is_first_ac: false }
    }
  }
]

export const MOCK_CONTEST_OI_RANK = [
  { id: 21, user: { id: 11, username: 'alice', real_name: 'Alice Chen' }, total_score: 200, submission_info: { 1001: 100, 1002: 100 } },
  { id: 22, user: { id: 13, username: 'charlie', real_name: 'Charlie Wang' }, total_score: 180, submission_info: { 1001: 100, 1002: 80 } },
  { id: 23, user: { id: 12, username: 'bob', real_name: 'Bob Li' }, total_score: 160, submission_info: { 1001: 80, 1002: 80 } },
  { id: 24, user: { id: 14, username: 'diana', real_name: 'Diana Zhao' }, total_score: 140, submission_info: { 1001: 60, 1002: 80 } },
  { id: 25, user: { id: 15, username: 'evan', real_name: 'Evan Sun' }, total_score: 90, submission_info: { 1001: 50, 1002: 40 } }
]

export const MOCK_ACM_HELPER = [
  { id: 1, username: 'alice', real_name: 'Alice Chen', problem_id: '1001', ac_info: { ac_time: 420, is_ac: true, is_first_ac: true }, checked: false },
  { id: 2, username: 'bob', real_name: 'Bob Li', problem_id: '1001', ac_info: { ac_time: 610, is_ac: true, is_first_ac: false }, checked: true },
  { id: 1, username: 'alice', real_name: 'Alice Chen', problem_id: '1002', ac_info: { ac_time: 840, is_ac: true, is_first_ac: false }, checked: false },
  { id: 4, username: 'diana', real_name: 'Diana Zhao', problem_id: '1002', ac_info: { ac_time: 1140, is_ac: true, is_first_ac: true }, checked: false }
]

function submissionIso (minutesAgo) {
  return new Date(Date.now() - minutesAgo * 60 * 1000).toISOString()
}

export const MOCK_SUBMISSIONS = ['1001', '1002'].flatMap((problem, problemIndex) => [
  { id: `mock-${problem}-1`, problem, username: 'alice', result: 0, language: 'C++', create_time: submissionIso(problemIndex * 3 + 4), statistic_info: { time_cost: 12, memory_cost: 16384 } },
  { id: `mock-${problem}-2`, problem, username: 'bob', result: 0, language: 'Python3', create_time: submissionIso(problemIndex * 3 + 16), statistic_info: { time_cost: 26, memory_cost: 18432 } },
  { id: `mock-${problem}-3`, problem, username: 'charlie', result: -1, language: 'C++', create_time: submissionIso(problemIndex * 3 + 32), statistic_info: { time_cost: 0, memory_cost: 0 } },
  { id: `mock-${problem}-4`, problem, username: 'diana', result: 0, language: 'Java', create_time: submissionIso(problemIndex * 3 + 51), statistic_info: { time_cost: 38, memory_cost: 24576 } },
  { id: `mock-${problem}-5`, problem, username: 'evan', result: 6, language: 'C++', create_time: submissionIso(problemIndex * 3 + 74), statistic_info: { time_cost: 0, memory_cost: 0 } }
])

export function cloneFixtures (items) {
  return items.map(item => JSON.parse(JSON.stringify(item)))
}

const developmentProblemFields = [
  'title', 'description', 'input_description', 'output_description', 'samples',
  'hint', 'source', 'tags', 'difficulty', 'rule_type', 'languages', 'template'
]

export function applyDevelopmentProblemFixture (problem) {
  if (!problem) return problem
  const displayId = String(problem._id)
  if (displayId === '1003') return null
  const fixture = MOCK_PROBLEMS.find(item => String(item._id) === displayId)
  if (!fixture) return problem
  const normalized = { ...problem }
  developmentProblemFields.forEach(field => {
    normalized[field] = JSON.parse(JSON.stringify(fixture[field]))
  })
  return normalized
}

export function applyDevelopmentProblemFixtures (problems = []) {
  return problems.map(applyDevelopmentProblemFixture).filter(Boolean)
}

export function applyDevelopmentContestFixtures (contests = []) {
  return contests.map(contest => {
    const fixture = MOCK_CONTESTS.find(item => String(item.id) === String(contest.id))
    if (!fixture) return contest
    return {
      ...contest,
      title: fixture.title,
      description: fixture.description,
      problem_ids: fixture.problem_ids.slice(),
      problems: fixture.problems.slice()
    }
  })
}

export function applyDevelopmentTagFixtures (tags = []) {
  return tags.filter(tag => !['special-judge', 'constructive'].includes(tag.name))
}

export function filterMockProblems (query = {}) {
  const keyword = String(query.keyword || '').trim().toLowerCase()
  return MOCK_PROBLEMS.filter(problem => {
    const matchesKeyword = !keyword || `${problem._id} ${problem.title}`.toLowerCase().includes(keyword)
    const matchesDifficulty = !query.difficulty || problem.difficulty === query.difficulty
    const matchesTag = !query.tag || (problem.tags || []).includes(query.tag)
    return matchesKeyword && matchesDifficulty && matchesTag
  })
}

export function filterMockContests (query = {}) {
  return MOCK_CONTESTS.filter(contest => {
    const matchesKeyword = !query.keyword || contest.title.toLowerCase().includes(String(query.keyword).toLowerCase())
    const matchesRule = !query.rule_type || contest.rule_type === query.rule_type
    const matchesStatus = query.status === '' || query.status === undefined || contest.status === String(query.status)
    return matchesKeyword && matchesRule && matchesStatus
  })
}
