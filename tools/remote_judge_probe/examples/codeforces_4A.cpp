#include <iostream>

int main() {
    int weight;
    std::cin >> weight;
    std::cout << (weight > 2 && weight % 2 == 0 ? "YES" : "NO") << '\n';
    return 0;
}
