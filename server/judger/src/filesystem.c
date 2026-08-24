#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/landlock.h>
#include <stddef.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

#include "filesystem.h"


int restrict_file_writes_to_cwd(void) {
#if !defined(__NR_landlock_create_ruleset) || !defined(__NR_landlock_add_rule) || \
    !defined(__NR_landlock_restrict_self)
    errno = ENOSYS;
    return -1;
#else
    int abi = (int) syscall(__NR_landlock_create_ruleset, NULL, 0,
                            LANDLOCK_CREATE_RULESET_VERSION);
    // File IO requires ABI 3 so O_TRUNC/truncate are part of the handled
    // access set. ABI 1/2 cannot enforce the fixed-directory write boundary.
    if (abi < 3) {
        errno = EOPNOTSUPP;
        return -1;
    }

    __u64 write_access = LANDLOCK_ACCESS_FS_WRITE_FILE |
                         LANDLOCK_ACCESS_FS_REMOVE_DIR |
                         LANDLOCK_ACCESS_FS_REMOVE_FILE |
                         LANDLOCK_ACCESS_FS_MAKE_CHAR |
                         LANDLOCK_ACCESS_FS_MAKE_DIR |
                         LANDLOCK_ACCESS_FS_MAKE_REG |
                         LANDLOCK_ACCESS_FS_MAKE_SOCK |
                         LANDLOCK_ACCESS_FS_MAKE_FIFO |
                         LANDLOCK_ACCESS_FS_MAKE_BLOCK |
                         LANDLOCK_ACCESS_FS_MAKE_SYM;
#ifdef LANDLOCK_ACCESS_FS_REFER
    if (abi >= 2) {
        write_access |= LANDLOCK_ACCESS_FS_REFER;
    }
#endif
#ifdef LANDLOCK_ACCESS_FS_TRUNCATE
    if (abi >= 3) {
        write_access |= LANDLOCK_ACCESS_FS_TRUNCATE;
    }
#endif

    const struct landlock_ruleset_attr ruleset_attr = {
        .handled_access_fs = write_access,
    };
    int ruleset_fd = (int) syscall(__NR_landlock_create_ruleset,
                                   &ruleset_attr, sizeof(ruleset_attr), 0);
    if (ruleset_fd < 0) {
        return -1;
    }

    int cwd_fd = open(".", O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (cwd_fd < 0) {
        int saved_errno = errno;
        close(ruleset_fd);
        errno = saved_errno;
        return -1;
    }

    const struct landlock_path_beneath_attr path_beneath = {
        .allowed_access = write_access,
        .parent_fd = cwd_fd,
    };
    if (syscall(__NR_landlock_add_rule, ruleset_fd,
                LANDLOCK_RULE_PATH_BENEATH, &path_beneath, 0) != 0 ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0 ||
        syscall(__NR_landlock_restrict_self, ruleset_fd, 0) != 0) {
        int saved_errno = errno;
        close(cwd_fd);
        close(ruleset_fd);
        errno = saved_errno;
        return -1;
    }

    close(cwd_fd);
    close(ruleset_fd);
    return 0;
#endif
}
