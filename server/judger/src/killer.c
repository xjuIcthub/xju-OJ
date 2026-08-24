#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <sys/types.h>

#include "killer.h"


int kill_process_group(pid_t process_group) {
    if (process_group <= 0) {
        errno = EINVAL;
        return -1;
    }
    if (kill(-process_group, SIGKILL) == 0 || errno == ESRCH) {
        return 0;
    }
    return -1;
}
