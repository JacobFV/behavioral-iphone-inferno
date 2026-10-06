/* Owned SDK-free bounded APFS growth experiment; no Apple implementation code. */
typedef unsigned long size_t;
typedef unsigned long long u64;
typedef unsigned int u32;
extern int printf(const char *, ...), fflush(void *), strcmp(const char *, const char *);
extern int access(const char *, int), fork(void), execve(const char *, char *const[], char *const[]);
extern int waitpid(int, int *, int), unmount(const char *, int), *__error(void);
extern int open(const char *, int, ...), close(int);
extern long read(int, void *, size_t);
extern void _exit(int), sync(void);
extern unsigned int sleep(unsigned int);
extern void *dlopen(const char *, int), *dlsym(void *, const char *);
extern const char *dlerror(void);
struct filesystem_space {
    u32 block_size; int io_size;
    u64 blocks, free_blocks, available_blocks, files, free_files;
    int fsid[2]; u32 owner, type, flags, subtype;
    char type_name[16], mounted_on[1024], mounted_from[1024];
    u32 extended_flags, reserved[7];
};
extern int statfs(const char *, struct filesystem_space *);
_Static_assert(sizeof(struct filesystem_space) == 2168, "Darwin statfs64 ABI");
static int mount_system(void) {
    char *args[] = {"/sbin/mount_apfs", "-o", "ro", "/dev/disk0s1s1", "/mnt1", 0};
    int pid = fork();
    if (pid == 0) { char *env[] = {"PATH=/usr/bin:/bin:/usr/sbin:/sbin", 0}; execve(args[0], args, env); _exit(127); }
    if (pid < 0) return -1;
    int status = -1;
    while (waitpid(pid, &status, 0) < 0) if (*__error() != 4) return -1;
    printf("INFERNO_GROW_MOUNT raw_status=%d\n", status); fflush(0);
    return status;
}
/* FNV-1a plus exact length is a guest before/after consistency check, not a cryptographic digest. */
static int fingerprint(const char *path, u64 *hash, u64 *bytes) {
    int fd = open(path, 0);
    if (fd < 0) return -1;
    unsigned char buffer[16384];
    u64 h = 14695981039346656037ULL, count = 0;
    for (;;) {
        long n = read(fd, buffer, sizeof(buffer));
        if (n < 0) { close(fd); return -1; }
        if (!n) break;
        count += n;
        for (long i=0; i<n; i++) { h ^= buffer[i]; h *= 1099511628211ULL; }
    }
    close(fd); *hash = h; *bytes = count;
    printf("INFERNO_GROW_FILE %s bytes=%llu fnv1a64=%016llx\n", path, count, h); fflush(0);
    return 0;
}
static int inspect(struct filesystem_space *space, u64 hashes[2], u64 lengths[2]) {
    if (mount_system()) return -1;
    int result = statfs("/mnt1", space);
    if (!result) {
        printf("INFERNO_GROW_SPACE block_size=%u blocks=%llu available=%llu\n", space->block_size, space->blocks, space->available_blocks); fflush(0);
        result = fingerprint("/mnt1/System/Library/CoreServices/SystemVersion.plist", &hashes[0], &lengths[0]);
        if (!result) result = fingerprint("/mnt1/sbin/launchd", &hashes[1], &lengths[1]);
    }
    int unmounted = unmount("/mnt1", 0);
    printf("INFERNO_GROW_UNMOUNT result=%d errno=%d\n", unmounted, *__error()); fflush(0);
    return result || unmounted ? -1 : 0;
}
int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--disposable-root-copy")) return 2;
    /* 32GiB disk, 4096-byte sectors, APFS start256, end8388602. */
    const u64 requested_bytes = (8388602ULL - 256 + 1) * 4096;
    printf("INFERNO_GROW_BEGIN device=/dev/disk0s1 requested_bytes=%llu\n", requested_bytes); fflush(0);
    for (int i=0; access("/dev/disk0s1s1", 0) && i<30; i++) sleep(1);
    if (access("/dev/disk0s1s1", 0)) return 3;
    struct filesystem_space before, after;
    u64 before_hashes[2], after_hashes[2], before_lengths[2], after_lengths[2];
    if (inspect(&before, before_hashes, before_lengths)) return 4;
    if (before.block_size != 4096 || before.blocks >= requested_bytes / 4096) return 5;
    void *framework = dlopen("/System/Library/PrivateFrameworks/APFS.framework/APFS", 1);
    if (!framework) { printf("INFERNO_GROW_DLOPEN_FAILED %s\n", dlerror()); fflush(0); return 6; }
    int (*resize)(const char *, u64) = (int (*)(const char *, u64))dlsym(framework, "APFSContainerResize");
    if (!resize) { printf("INFERNO_GROW_DLSYM_FAILED %s\n", dlerror()); fflush(0); return 7; }
    int result = resize("/dev/disk0s1", requested_bytes);
    printf("INFERNO_GROW_API_RETURN status=%d hex=%08x\n", result, (unsigned int)result); fflush(0);
    sync();
    if (result) return 8;
    if (inspect(&after, after_hashes, after_lengths)) return 9;
    for (int i=0; i<2; i++) if (before_hashes[i] != after_hashes[i] || before_lengths[i] != after_lengths[i]) return 10;
    if (after.block_size != before.block_size || after.blocks <= before.blocks || after.blocks * after.block_size < 31ULL*1024*1024*1024) return 11;
    sync();
    printf("INFERNO_GROW_COMPLETE before_blocks=%llu after_blocks=%llu file_consistency=pass\n", before.blocks, after.blocks); fflush(0);
    return 0;
}
