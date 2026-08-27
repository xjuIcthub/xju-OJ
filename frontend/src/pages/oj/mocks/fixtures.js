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
    title: 'A+B with Integers',
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
    source: 'XJU-OJ warm-up set',
    test_case_id: 'mock-a-plus-b-int',
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
    title: 'A+B with Doubles',
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
    source: 'XJU-OJ precision set',
    test_case_id: 'mock-a-plus-b-double',
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
  {
    _id: '1003',
    title: 'Special Judge A+B',
    difficulty: 'High',
    rule_type: 'ACM',
    submission_number: 164,
    accepted_number: 97,
    tags: ['special-judge', 'constructive'],
    spj: true,
    visible: true,
    my_status: null,
    id: '1003',
    description: '<p>Read two integers <code>a</code> and <code>b</code>. Output any two integers <code>x</code> and <code>y</code> satisfying <code>x + y = a + b</code>. This problem uses a Special Judge.</p>',
    input_description: '<p>The only line contains two integers <code>a</code> and <code>b</code>.</p>',
    output_description: '<p>Output any two integers <code>x</code> and <code>y</code> whose sum equals <code>a + b</code>.</p>',
    samples: [{ input: '7 8', output: '10 5' }],
    hint: 'The checker validates the arithmetic relation instead of comparing one fixed output string.',
    source: 'XJU-OJ special judge set',
    test_case_id: 'mock-a-plus-b-spj',
    spj_language: 'C++',
    spj_code: '#include <fstream>\nint main(int argc, char** argv) {\n    std::ifstream in(argv[1]);\n    std::ifstream out(argv[2]);\n    long long a, b, x, y;\n    if (!(in >> a >> b) || !(out >> x >> y)) return 1;\n    return x + y == a + b ? 0 : 1;\n}',
    spj_compile_ok: true,
    spj_version: 'mock-spj-a-plus-b',
    test_case_score: [{ input_name: '1.in', score: 0 }],
    time_limit: 1000,
    memory_limit: 128,
    io_mode: { io_mode: 'Standard IO' },
    created_by: { username: 'XJU-ICTHub' },
    languages: ['C++', 'Python3'],
    template: {
      'C++': '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    long long a, b;\n    cin >> a >> b;\n    cout << a << " " << b << "\\n";\n    return 0;\n}',
      Python3: 'a, b = map(int, input().split())\nprint(a, b)'
    },
    statistic_info: { '0': 97, '-1': 67 }
  }
]

export const MOCK_CONTESTS = [
  {
    id: 101,
    title: 'A+B Warm-up Contest',
    start_time: isoFromNow(2, 19),
    end_time: isoFromNow(2, 21),
    rule_type: 'ACM',
    contest_type: 'Public',
    status: '1',
    problem_ids: ['1001', '1002'],
    problems: ['1001', '1002'],
    description: '<h3>Contest overview</h3><p>Start with the integer A+B warm-up, then handle decimal precision carefully. Both problems are selected from the public problem set.</p>',
    now: new Date().toISOString(),
    created_by: { id: 'mock-admin', username: 'XJU-ICTHub' },
    real_time_rank: true
  },
  {
    id: 102,
    title: 'Special Judge Challenge',
    start_time: isoFromNow(7, 14),
    end_time: isoFromNow(7, 17),
    rule_type: 'OI',
    contest_type: 'Public',
    status: '1',
    problem_ids: ['1002', '1003'],
    problems: ['1002', '1003'],
    description: '<h3>Contest overview</h3><p>This challenge combines floating-point output with a Special Judge. Each contestant solves exactly the two listed problems.</p>',
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

function submissionIso (minutesAgo) {
  return new Date(Date.now() - minutesAgo * 60 * 1000).toISOString()
}

export const MOCK_SUBMISSIONS = ['1001', '1002', '1003'].flatMap((problem, problemIndex) => [
  { id: `mock-${problem}-1`, problem, username: 'alice', result: 0, language: 'C++', create_time: submissionIso(problemIndex * 3 + 4), statistic_info: { time_cost: 12, memory_cost: 16384 } },
  { id: `mock-${problem}-2`, problem, username: 'bob', result: 0, language: 'Python3', create_time: submissionIso(problemIndex * 3 + 16), statistic_info: { time_cost: 26, memory_cost: 18432 } },
  { id: `mock-${problem}-3`, problem, username: 'charlie', result: -1, language: 'C++', create_time: submissionIso(problemIndex * 3 + 32), statistic_info: { time_cost: 0, memory_cost: 0 } },
  { id: `mock-${problem}-4`, problem, username: 'diana', result: 0, language: 'Java', create_time: submissionIso(problemIndex * 3 + 51), statistic_info: { time_cost: 38, memory_cost: 24576 } },
  { id: `mock-${problem}-5`, problem, username: 'evan', result: 6, language: 'C++', create_time: submissionIso(problemIndex * 3 + 74), statistic_info: { time_cost: 0, memory_cost: 0 } }
])

export function cloneFixtures (items) {
  return items.map(item => JSON.parse(JSON.stringify(item)))
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
