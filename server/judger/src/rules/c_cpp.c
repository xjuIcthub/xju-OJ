#define _GNU_SOURCE
#include <stdbool.h>
#include <errno.h>
#include <fcntl.h>
#include <seccomp.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "../runner.h"


static int add_read_only_open_rule(scmp_filter_ctx ctx, int syscall_number, unsigned int flags_argument) {
    unsigned int forbidden_flags = O_ACCMODE | O_CREAT | O_TRUNC | O_APPEND;
#ifdef O_TMPFILE
    forbidden_flags |= O_TMPFILE & ~O_DIRECTORY;
#endif
    int result = seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscall_number, 1,
                                  SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ, forbidden_flags, 0));
    if (result != 0) {
        errno = -result;
        return LOAD_SECCOMP_FAILED;
    }
    return SUCCESS;
}


static int add_file_io_open_rules(scmp_filter_ctx ctx, int syscall_number,
                                  unsigned int flags_argument) {
    if (add_read_only_open_rule(ctx, syscall_number, flags_argument) != SUCCESS ||
        seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_ACCMODE, O_WRONLY)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_ACCMODE, O_RDWR)) != 0) {
        return LOAD_SECCOMP_FAILED;
    }
    return SUCCESS;
}


int _c_cpp_seccomp_rules(struct config *_config, bool allow_write_file) {
    int syscalls_whitelist[] = {
        SCMP_SYS(access),
        SCMP_SYS(arch_prctl),
        SCMP_SYS(brk),
        SCMP_SYS(clock_gettime),
        SCMP_SYS(clock_nanosleep),
        SCMP_SYS(nanosleep),
        SCMP_SYS(close),
        SCMP_SYS(exit_group),
        SCMP_SYS(faccessat),
        SCMP_SYS(fstat),
        SCMP_SYS(futex),
        SCMP_SYS(getcwd),
        SCMP_SYS(getrandom),
        SCMP_SYS(lseek),
        SCMP_SYS(mmap),
        SCMP_SYS(mprotect),
        SCMP_SYS(munmap),
        SCMP_SYS(newfstatat),
        SCMP_SYS(pread64),
        SCMP_SYS(prlimit64),
        SCMP_SYS(read),
        SCMP_SYS(readlink),
        SCMP_SYS(readlinkat),
        SCMP_SYS(readv),
        SCMP_SYS(rseq),
        SCMP_SYS(set_robust_list),
        SCMP_SYS(set_tid_address),
        SCMP_SYS(write),
        SCMP_SYS(writev)
    };
    int syscalls_whitelist_length = sizeof(syscalls_whitelist) / sizeof(int);
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL_PROCESS);
    if (!ctx) {
        return LOAD_SECCOMP_FAILED;
    }

    for (int i = 0; i < syscalls_whitelist_length; i++) {
        if (seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscalls_whitelist[i], 0) != 0) {
            seccomp_release(ctx);
            return LOAD_SECCOMP_FAILED;
        }
    }

    // This permits only child.c's initial execve call because seccomp compares
    // the userspace pointer, not the path string.
    if (seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(execve), 1,
                         SCMP_A0(SCMP_CMP_EQ, (scmp_datum_t) (_config->exe_path))) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }

    if (allow_write_file) {
        if (add_file_io_open_rules(ctx, SCMP_SYS(open), 1) != SUCCESS ||
            add_file_io_open_rules(ctx, SCMP_SYS(openat), 2) != SUCCESS) {
            seccomp_release(ctx);
            return LOAD_SECCOMP_FAILED;
        }
        int file_io_syscalls[] = {SCMP_SYS(dup), SCMP_SYS(dup2), SCMP_SYS(dup3)};
        int file_io_syscalls_length = sizeof(file_io_syscalls) / sizeof(int);
        for (int i = 0; i < file_io_syscalls_length; i++) {
            if (seccomp_rule_add(ctx, SCMP_ACT_ALLOW, file_io_syscalls[i], 0) != 0) {
                seccomp_release(ctx);
                return LOAD_SECCOMP_FAILED;
            }
        }
    }
    else {
        if (add_read_only_open_rule(ctx, SCMP_SYS(open), 1) != SUCCESS ||
            add_read_only_open_rule(ctx, SCMP_SYS(openat), 2) != SUCCESS) {
            seccomp_release(ctx);
            return LOAD_SECCOMP_FAILED;
        }
    }

    if (seccomp_load(ctx) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
    seccomp_release(ctx);
    return SUCCESS;
}


int c_cpp_seccomp_rules(struct config *_config) {
    return _c_cpp_seccomp_rules(_config, false);
}
