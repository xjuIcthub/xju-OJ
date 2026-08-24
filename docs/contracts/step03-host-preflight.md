# Step 03 Host Preflight

> Captured 2026-08-24 on target `huawei1` / `XJU-ICTHubS1`, using the remote host's Asia/Shanghai clock. This records the non-production preflight; no new service was started and no secret was generated.

## Host and container gates

| Gate | Observed value | Result |
|---|---|---|
| OS | Ubuntu 22.04.5 LTS (`VERSION_ID=22.04`) | pass |
| Kernel/arch | 5.15.0-186-generic, x86_64 | pass; amd64 production lane |
| cgroup | `cgroup2fs`; Docker reports cgroup v2 | pass |
| systemd | 249.11-0ubuntu3.21 | recorded |
| time/locale | `Asia/Shanghai`, NTP synchronized, `en_US.UTF-8` | pass |
| root filesystem | ext4, `rw,relatime`; `/srv` and `/var/backups` share `/dev/vda1` | recorded |
| space | 40G total, 17G used, 22G available, 45% | pass for empty preflight roots; production restore sizing remains Step 19 |
| inode | 2,621,440 total, 377,325 used, 15% | pass |
| Docker Engine | 29.7.1; containerd 2.2.6; runc 1.3.6 | pass |
| Compose | v5.4.0 | supports `up --wait` |
| Buildx/BuildKit | Buildx 0.36.0; BuildKit v0.32.0 | pass |
| Docker security | AppArmor, builtin seccomp, cgroupns; not rootless | recorded |

The engine-managed `default` Buildx builder is running with the Docker driver and persistent BuildKit cache policy. It exposes only `linux/amd64` (plus amd64 v2/v3/v4 variants); no arm64 worker or separate arm64 cache was created on this amd64 host. Arm64 remains an experimental later gate, not an unverified production claim.

## Network and firewall

- UFW reports `inactive`.
- nftables/iptables reports IPv4 Docker `FORWARD` policy `DROP`; IPv6 `FORWARD` policy is `ACCEPT`.
- Docker currently forwards host TCP 80 and 443 to the existing backend container (`172.18.0.5:8000` and `:1443`). No host listeners were observed on 8000, 8080, 5432, or 6379.
- Host listeners observed were SSH 22, HTTP 80, HTTPS 443, loopback-only service ports, and local DNS. No firewall rule was changed in this Step.
- The IPv6 forwarding `ACCEPT` policy is a security review item. It is explained and recorded rather than silently changed while the current Compose topology still differs from the target topology.

## Capability checks

The target exposes the required command capabilities:

- `docker compose up --help` includes `--wait` and `--wait-timeout`.
- `docker buildx build --help` includes `--cache-from`, `--cache-to`, and `--secret`.
- `docker buildx inspect --bootstrap` succeeds with the running default builder.

## Gate result

The Ubuntu, cgroup, Docker/Compose/BuildKit, capacity, and firewall-observation gates passed for a non-production preflight. Production release remains closed until the external Secret-file gate in `step03-runtime-preflight.md` is satisfied; no Step 04 or image release is claimed by this record.
