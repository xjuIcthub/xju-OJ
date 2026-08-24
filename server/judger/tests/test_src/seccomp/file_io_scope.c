#include <errno.h>
#include <fcntl.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 3) {
        return 1;
    }
    int local_fd = open(argv[1], O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (local_fd < 0) {
        return 2;
    }
    close(local_fd);

    errno = 0;
    int escape_fd = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (escape_fd >= 0) {
        close(escape_fd);
        return 3;
    }
    return errno == EACCES || errno == EPERM ? 0 : 4;
}
