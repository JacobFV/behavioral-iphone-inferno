/* Owned SDK-free recovery helper. ABI declarations only; guest libSystem supplies implementation. */
typedef unsigned long size_t;
typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
extern int printf(const char *, ...), snprintf(char *, size_t, const char *, ...);
extern int fflush(void *), strcmp(const char *, const char *), access(const char *, int);
extern int fork(void), execve(const char *, char *const[], char *const[]);
extern int waitpid(int, int *, int), mkdir(const char *, uint16_t), unmount(const char *, int);
extern int *__error(void);
extern void _exit(int), sync(void);
extern unsigned int sleep(unsigned int);
/* Darwin 64-bit dirent ABI (xnu-7195.141.2/bsd/sys/dirent.h). */
struct directory_entry { unsigned long long inode, seekoff; uint16_t reclen, namelen; unsigned char type; char name[1024]; };
extern void *opendir(const char *);
extern struct directory_entry *readdir(void *);
extern int closedir(void *), open(const char *, int, ...), close(int);
extern long read(int, void *, size_t);
extern long long lseek(int, long long, int);
static void devices(void) {
    void *directory = opendir("/dev");
    if (!directory) return;
    struct directory_entry *entry;
    while ((entry = readdir(directory))) {
        const char *n = entry->name;
        if ((n[0]=='d' && n[1]=='i' && n[2]=='s' && n[3]=='k') ||
            (n[0]=='r' && n[1]=='d' && n[2]=='i' && n[3]=='s' && n[4]=='k'))
            printf("INFERNO_PREP_DEVICE %s type=%u\n", n, entry->type);
    }
    closedir(directory);
    int fd = open("/dev/rdisk0", 0);
    if (fd >= 0) {
        unsigned char data[4096];
        if (lseek(fd, 4096, 0) == 4096 && read(fd, data, sizeof(data)) == (long)sizeof(data)) {
            printf("INFERNO_PREP_DISK0_OFFSET4096 ");
            for (int i=0;i<32;i++) printf("%02x", data[i]);
            printf("\n");
        }
        close(fd);
    }
    fflush(0);
}
extern int copyfile(const char *, const char *, void *, uint32_t);
/* Darwin attr.h: fixed ABI, bitmapcount=5; ATTR_VOL_INFO|ATTR_VOL_NAME. */
struct attrs { uint16_t count, reserved; uint32_t common, volume, directory, file, fork; };
struct volume_name { uint32_t size; int offset; uint32_t length; char data[1024]; };
extern int getattrlist(const char *, struct attrs *, void *, size_t, unsigned long);
static int run(char *const argv[]) {
    printf("INFERNO_PREP_EXEC");
    for (int i = 0; argv[i]; ++i) printf(" %s", argv[i]);
    printf("\n"); fflush(0);
    int pid = fork();
    if (pid == 0) { char *env[] = {"PATH=/usr/bin:/bin:/usr/sbin:/sbin", 0}; execve(argv[0], argv, env); _exit(127); }
    if (pid < 0) return -1;
    int status = -1;
    while (waitpid(pid, &status, 0) < 0) if (*__error() != 4) return -1;
    printf("INFERNO_PREP_STATUS raw=%d\n", status); fflush(0);
    return status;
}
static int mount_at(const char *device, const char *point, int readonly) {
    char *args[] = {"/sbin/mount_apfs", "-o", readonly ? "ro" : "rw", (char *)device, (char *)point, 0};
    return run(args);
}
static int volume_name(const char *point, char *out, size_t capacity) {
    struct attrs attrs = {5, 0, 0, 0x80002000, 0, 0, 0};
    struct volume_name name = {0};
    if (getattrlist(point, &attrs, &name, sizeof(name), 0) != 0) return -1;
    if (name.offset < 8 || (unsigned long)name.offset + 4 + name.length > sizeof(name) || !name.length) return -1;
    char *value = (char *)&name.offset + name.offset;
    if (value[name.length - 1] != 0) return -1;
    snprintf(out, capacity, "%s", value);
    return 0;
}
static int ensure(const char *path) {
    if (!mkdir(path, 0755) || *__error() == 17) return 0;
    printf("INFERNO_PREP_MKDIR_FAILED %s errno=%d\n", path, *__error());
    return -1;
}
int main(int argc, char **argv) {
    if (argc < 2 || strcmp(argv[1], "--disposable-root-copy")) return 2;
    int roles = 0, existing = 0, gigalocker = 0;
    for (int i=2; i<argc; ++i) {
        if (!strcmp(argv[i], "--role-volumes")) roles = 1;
        else if (!strcmp(argv[i], "--existing-volumes")) existing = 1;
        else if (!strcmp(argv[i], "--init-gigalocker")) gigalocker = 1;
        else return 2;
    }
    printf("INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=%d roles=%d gigalocker=%d\n", existing, roles, gigalocker); fflush(0);
    for (int i = 0; access("/dev/disk0s1", 0) && i < 30; ++i) sleep(1);
    if (access("/dev/disk0s1", 0)) { devices(); return 3; }
    devices();
    char *preboot[] = {"/sbin/newfs_apfs", "-A", "-o", "role=b", "-v", "Preboot", "/dev/disk0s1", 0};
    if (!existing && run(preboot)) return 4;
    if (!existing && roles) {
        char *xart[] = {"/sbin/newfs_apfs", "-s10485760", "-A", "-o", "role=x", "-v", "xART", "/dev/disk0s1", 0};
        char *hardware[] = {"/sbin/newfs_apfs", "-s25165824", "-A", "-o", "role=h", "-v", "Hardware", "/dev/disk0s1", 0};
        if (run(xart) || run(hardware)) return 4;
    }
    char system_device[64] = {0}, preboot_device[64] = {0}, xart_device[64] = {0};
    /* Discover actual volume identities, never infer an index from creation order. */
    for (int i = 1; i <= 16; ++i) {
        char device[64], name[1024];
        snprintf(device, sizeof(device), "/dev/disk0s1s%d", i);
        if (access(device, 0)) continue;
        if (mount_at(device, "/mnt1", 1)) continue;
        int result = volume_name("/mnt1", name, sizeof(name));
        if (!result) {
            printf("INFERNO_PREP_VOLUME %s name=%s\n", device, name); fflush(0);
            if (!access("/mnt1/System/Library/CoreServices/SystemVersion.plist", 0) &&
                !access("/mnt1/usr/standalone/firmware", 0))
                snprintf(system_device, sizeof(system_device), "%s", device);
            if (!strcmp(name, "xART")) snprintf(xart_device, sizeof(xart_device), "%s", device);
            if (!strcmp(name, "Preboot")) snprintf(preboot_device, sizeof(preboot_device), "%s", device);
        }
        if (unmount("/mnt1", 0)) return 5;
        if (result) return 6;
    }
    if (!system_device[0] || !preboot_device[0]) { printf("INFERNO_PREP_MISSING_VOLUME\n"); return 7; }
    if (!existing) {
    if (mount_at(system_device, "/mnt1", 1) || mount_at(preboot_device, "/mnt2", 0)) return 8;
    const char *prefix = "/mnt2/000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";
    char path[256];
    if (ensure(prefix)) return 9;
    snprintf(path, sizeof(path), "%s/usr", prefix); if (ensure(path)) return 9;
    snprintf(path, sizeof(path), "%s/usr/standalone", prefix); if (ensure(path)) return 9;
    snprintf(path, sizeof(path), "%s/usr/standalone/firmware", prefix);
    /* copyfile.h: ALL=15, RECURSIVE=1<<15, NOFOLLOW=(1<<18)|(1<<19). */
    if (copyfile("/mnt1/usr/standalone/firmware", path, 0, 15 | (1 << 15) | (1 << 18) | (1 << 19))) {
        printf("INFERNO_PREP_COPY_FAILED errno=%d\n", *__error()); fflush(0); return 10;
    }
    sync();
    if (unmount("/mnt2", 0) || unmount("/mnt1", 0)) return 11;
    }
    if (gigalocker) {
        if (!xart_device[0] || ensure("/mnt7") || mount_at(xart_device, "/mnt7", 0)) return 12;
        char *init[] = {"/usr/libexec/seputil", "--gigalocker-init", 0};
        if (run(init)) return 13;
        sync();
        if (unmount("/mnt7", 0)) return 14;
        printf("INFERNO_GIGALOCKER_COMPLETE: original seputil initialization and clean unmount succeeded\n"); fflush(0);
    }
    printf("INFERNO_PREP_COMPLETE: Preboot added, original firmware copied\n"); fflush(0);
    return 0;
}
