#include <array>
#include <cstdint>
#include <iostream>

using Matrix = std::array<std::array<std::int64_t, 4>, 4>;
constexpr std::int64_t MOD = 998244353;

Matrix multiply(const Matrix &left, const Matrix &right) {
    Matrix result{};
    for (int i = 0; i < 4; ++i) {
        for (int k = 0; k < 4; ++k) {
            for (int j = 0; j < 4; ++j) {
                result[i][j] = (result[i][j] + left[i][k] * right[k][j]) % MOD;
            }
        }
    }
    return result;
}

Matrix power(Matrix base, std::uint64_t exponent) {
    Matrix result{};
    for (int i = 0; i < 4; ++i) result[i][i] = 1;
    while (exponent > 0) {
        if (exponent & 1U) result = multiply(result, base);
        base = multiply(base, base);
        exponent >>= 1U;
    }
    return result;
}

int main() {
    std::uint64_t n;
    int target;
    std::cin >> n >> target;
    Matrix transition{};
    for (int residue = 0; residue < 4; ++residue) {
        for (int value : {0, 1, 3}) {
            ++transition[residue][(residue + value) % 4];
        }
    }
    std::cout << power(transition, n)[0][target] << '\n';
    return 0;
}
