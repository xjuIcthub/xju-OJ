#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <sched.h>
#include <seccomp.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>

#include "../runner.h"


static int add_write_open_rules(scmp_filter_ctx ctx, int syscall_number, unsigned int flags_argument) {
    if (seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_ACCMODE, O_WRONLY)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_ACCMODE, O_RDWR)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_CREAT, O_CREAT)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_TRUNC, O_TRUNC)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_APPEND, O_APPEND)) != 0) {
        return LOAD_SECCOMP_FAILED;
    }
#ifdef O_TMPFILE
    if (seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscall_number, 1,
                         SCMP_CMP(flags_argument, SCMP_CMP_MASKED_EQ,
                                  O_TMPFILE & ~O_DIRECTORY,
                                  O_TMPFILE & ~O_DIRECTORY)) != 0) {
        return LOAD_SECCOMP_FAILED;
    }
#endif
    return SUCCESS;
}


int node_seccomp_rules(struct config *_config) {
    bool allow_write_file = strcmp(_config->seccomp_rule_name, "node_file_io") == 0;
    int syscalls_blacklist[] = {
        SCMP_SYS(socket),
        SCMP_SYS(socketpair),
        SCMP_SYS(kill),
        SCMP_SYS(tkill),
        SCMP_SYS(setsid),
        SCMP_SYS(setpgid),
        SCMP_SYS(unshare),
        SCMP_SYS(setns),
        SCMP_SYS(ptrace),
        SCMP_SYS(process_vm_readv),
        SCMP_SYS(process_vm_writev),
        SCMP_SYS(creat),
        SCMP_SYS(truncate),
        SCMP_SYS(ftruncate),
        SCMP_SYS(rename),
        SCMP_SYS(renameat),
        SCMP_SYS(unlink),
        SCMP_SYS(unlinkat),
        SCMP_SYS(link),
        SCMP_SYS(linkat),
        SCMP_SYS(symlink),
        SCMP_SYS(symlinkat),
        SCMP_SYS(mkdir),
        SCMP_SYS(mkdirat),
        SCMP_SYS(rmdir),
        SCMP_SYS(mknod),
        SCMP_SYS(mknodat),
        SCMP_SYS(chmod),
        SCMP_SYS(fchmod),
        SCMP_SYS(fchmodat),
        SCMP_SYS(chown),
        SCMP_SYS(fchown),
        SCMP_SYS(lchown),
        SCMP_SYS(fchownat),
        SCMP_SYS(utime),
        SCMP_SYS(utimes),
        SCMP_SYS(futimesat),
        SCMP_SYS(utimensat),
        SCMP_SYS(setxattr),
        SCMP_SYS(lsetxattr),
        SCMP_SYS(fsetxattr),
        SCMP_SYS(removexattr),
        SCMP_SYS(lremovexattr),
        SCMP_SYS(fremovexattr),
        SCMP_SYS(fallocate),
        SCMP_SYS(memfd_create),

#ifdef __NR_renameat2
        SCMP_SYS(renameat2),
#endif
#ifdef __NR_pidfd_send_signal
        SCMP_SYS(pidfd_send_signal),
#endif
#ifdef __NR_pidfd_open
        SCMP_SYS(pidfd_open),
#endif
#ifdef __NR_pidfd_getfd
        SCMP_SYS(pidfd_getfd),
#endif
    };
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
    if (!ctx) {
        return LOAD_SECCOMP_FAILED;
    }

    int blacklist_length = sizeof(syscalls_blacklist) / sizeof(int);
    for (int i = 0; i < blacklist_length; i++) {
        if (seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, syscalls_blacklist[i], 0) != 0) {
            seccomp_release(ctx);
            return LOAD_SECCOMP_FAILED;
        }
    }

    // V8/libuv need clone for threads. Block process-style clone and all later
    // exec attempts while allowing the initial child.c execve pointer.
    pid_t self_pid = getpid();
    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(fork), 0) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(vfork), 0) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(clone), 1,
                         SCMP_CMP(0, SCMP_CMP_MASKED_EQ, CLONE_THREAD, 0)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(execve), 1,
                         SCMP_A0(SCMP_CMP_NE, (scmp_datum_t) _config->exe_path)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, SCMP_SYS(tgkill), 1,
                         SCMP_A0(SCMP_CMP_NE, (scmp_datum_t) self_pid)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, SCMP_SYS(rt_sigqueueinfo), 1,
                         SCMP_A0(SCMP_CMP_NE, (scmp_datum_t) self_pid)) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_KILL_PROCESS, SCMP_SYS(rt_tgsigqueueinfo), 1,
                         SCMP_A0(SCMP_CMP_NE, (scmp_datum_t) self_pid)) != 0 ||
        (!allow_write_file &&
         (add_write_open_rules(ctx, SCMP_SYS(open), 1) != SUCCESS ||
          add_write_open_rules(ctx, SCMP_SYS(openat), 2) != SUCCESS))) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
#ifdef __NR_execveat
    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(execveat), 0) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
#endif
#ifdef __NR_clone3
    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(ENOSYS), SCMP_SYS(clone3), 0) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
#endif
#ifdef __NR_openat2
    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(ENOSYS), SCMP_SYS(openat2), 0) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
#endif
#ifdef __NR_io_uring_setup
    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(ENOSYS), SCMP_SYS(io_uring_setup), 0) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ERRNO(ENOSYS), SCMP_SYS(io_uring_enter), 0) != 0 ||
        seccomp_rule_add(ctx, SCMP_ACT_ERRNO(ENOSYS), SCMP_SYS(io_uring_register), 0) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
#endif

    if (seccomp_load(ctx) != 0) {
        seccomp_release(ctx);
        return LOAD_SECCOMP_FAILED;
    }
    seccomp_release(ctx);
    return SUCCESS;
}
