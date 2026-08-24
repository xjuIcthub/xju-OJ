#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    int fd;
    if (argc != 2) {
        return 2;
    }
    fd = open(argv[1], O_RDONLY | O_CREAT, 0600);
    if (fd < 0) {
        return 1;
    }
    close(fd);
    return 0;
}
