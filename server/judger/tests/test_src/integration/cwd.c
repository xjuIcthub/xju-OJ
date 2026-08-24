#include <limits.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        return 1;
    }
    puts(cwd);
    return 0;
}
