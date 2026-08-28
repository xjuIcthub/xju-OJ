#include <iostream>
#include <string>
#include <vector>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int n = 0;
    int m = 0;
    if (!(std::cin >> n >> m)) {
        return 0;
    }

    std::vector<long long> counts(1 << m, 0);
    for (int i = 0; i < n; ++i) {
        std::string channels;
        std::cin >> channels;
        int mask = 0;
        for (int j = 0; j < m; ++j) {
            if (channels[j] == '1') {
                mask |= 1 << j;
            }
        }
        ++counts[mask];
    }

    long long answer = 0;
    for (int left = 1; left < (1 << m); ++left) {
        for (int right = left; right < (1 << m); ++right) {
            if ((left & right) == 0) {
                continue;
            }
            if (left == right) {
                answer += counts[left] * (counts[left] - 1) / 2;
            } else {
                answer += counts[left] * counts[right];
            }
        }
    }

    std::cout << answer << '\n';
    return 0;
}
