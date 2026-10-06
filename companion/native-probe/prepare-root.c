/* Owned SDK-free recovery helper. ABI declarations only; guest libSystem supplies implementation. */
typedef unsigned long size_t;
typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
extern int printf(const char *, ...), snprintf(char *, size_t, const char *, ...);
extern int fflush(void *), strcmp(const char *, const char *), access(const char *, int);
extern int setuid(unsigned), setgid(unsigned), setgroups(int,const unsigned *);
extern int fork(void), execve(const char *, char *const[], char *const[]);
extern int waitpid(int, int *, int), mkdir(const char *, uint16_t), unmount(const char *, int);
extern int *__error(void);
extern void *dlopen(const char *, int), *dlsym(void *, const char *);
extern char *dlerror(void);
extern void _exit(int), sync(void);
extern unsigned int sleep(unsigned int);
/* Darwin 64-bit dirent ABI (xnu-7195.141.2/bsd/sys/dirent.h). */
struct directory_entry { unsigned long long inode, seekoff; uint16_t reclen, namelen; unsigned char type; char name[1024]; };
extern void *opendir(const char *);
extern struct directory_entry *readdir(void *);
extern int closedir(void *), open(const char *, int, ...), close(int);
extern long read(int, void *, size_t), write(int,const void *,size_t);
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
/* Darwin mount.h statfs64 ABI. Only filesystem space is logged. */
struct filesystem_space {
    uint32_t block_size; int io_size;
    unsigned long long blocks, free_blocks, available_blocks, files, free_files;
    int fsid[2]; uint32_t owner, type, flags, subtype;
    char type_name[16], mounted_on[1024], mounted_from[1024];
    uint32_t extended_flags, reserved[7];
};
extern int statfs(const char *, struct filesystem_space *);
_Static_assert(sizeof(struct filesystem_space) == 2168, "Darwin statfs64 ABI");
static int space(const char *point, const char *stage) {
    struct filesystem_space fs;
    if (statfs(point, &fs)) return -1;
    printf("INFERNO_SPACE %s block_size=%u available_blocks=%llu available_bytes=%llu\n",
           stage, fs.block_size, fs.available_blocks, fs.available_blocks * fs.block_size); fflush(0);
    return 0;
}
static int copy_contents(const char *source, const char *destination) {
    void *directory = opendir(source);
    if (!directory) return -1;
    struct directory_entry *entry;
    int error = 0;
    while ((entry = readdir(directory))) {
        if (!strcmp(entry->name, ".") || !strcmp(entry->name, "..")) continue;
        char from[2048], to[2048];
        int from_size = snprintf(from, sizeof(from), "%s/%s", source, entry->name);
        int to_size = snprintf(to, sizeof(to), "%s/%s", destination, entry->name);
        if (from_size < 0 || from_size >= sizeof(from) || to_size < 0 || to_size >= sizeof(to)) { error = -1; break; }
        printf("INFERNO_COPY %s -> %s\n", from, to); fflush(0);
        if (copyfile(from, to, 0, 15 | (1 << 15) | (1 << 18) | (1 << 19))) { error = -1; break; }
    }
    if (error) { printf("INFERNO_COPY_FAILED errno=%d\n", *__error()); fflush(0); }
    closedir(directory);
    if (!error) error = copyfile(source, destination, 0, 7 | (1 << 18) | (1 << 19));
    return error;
}
/* Darwin arm64 stat ABI: xnu-7195.141.2/bsd/sys/stat.h. */
struct file_stat {
    int dev; uint16_t mode, nlink; unsigned long long ino;
    uint32_t uid, gid; int rdev;
    long long times[8], size, blocks; int blksize;
    uint32_t flags, gen; int spare; long long qspare[2];
};
_Static_assert(sizeof(struct file_stat) == 144, "Darwin stat64 ABI");
extern int lstat(const char *, struct file_stat *);
extern long readlink(const char *, char *, size_t);
static unsigned long long verified_entries, verified_files, verified_bytes, verified_links, mismatches;
static void mismatch(const char *path, const char *reason) {
    ++mismatches; printf("INFERNO_TREE_MISMATCH %s reason=%s errno=%d\n", path, reason, *__error()); fflush(0);
}
static int child_path(char *out, size_t capacity, const char *parent, const char *name) {
    int n=snprintf(out,capacity,"%s/%s",parent,name);
    return n<0 || (size_t)n>=capacity ? -1 : 0;
}
static void compare_tree(const char *source, const char *destination) {
    struct file_stat a,b;
    if (lstat(source,&a) || lstat(destination,&b)) { mismatch(source,"lstat"); return; }
    ++verified_entries;
    if (a.mode != b.mode || a.uid != b.uid || a.gid != b.gid) mismatch(source,"mode/uid/gid");
    unsigned type=a.mode & 0xf000;
    if (type != (b.mode & 0xf000)) { mismatch(source,"type"); return; }
    if (type == 0x8000) {
        ++verified_files;
        if (a.size != b.size) mismatch(source,"size");
        int left=open(source,0),right=open(destination,0),equal=1;
        if(left<0 || right<0) { mismatch(source,"open"); if(left>=0)close(left); if(right>=0)close(right); return; }
        unsigned char x[16384],y[16384]; unsigned long long bytes=0;
        for (;;) {
            long n=read(left,x,sizeof(x)),m=read(right,y,sizeof(y));
            if(n<0 || m<0) { equal=0; break; }
            bytes+=n;
            if(n!=m)equal=0;
            if(n==m)for(long i=0;i<n;i++)if(x[i]!=y[i])equal=0;
            if(!n && !m)break;
        }
        close(left);close(right);verified_bytes+=bytes;
        if(!equal || bytes!=(unsigned long long)a.size)mismatch(source,"file-bytes");
    } else if(type == 0xa000) {
        char x[2048],y[2048]; long n=readlink(source,x,sizeof(x)),m=readlink(destination,y,sizeof(y));
        int equal=n>=0 && n==m && n<sizeof(x);
        if(equal)for(long i=0;i<n;i++)if(x[i]!=y[i])equal=0;
        if(!equal)mismatch(source,"symlink-target");
        ++verified_links;
    } else if(type == 0x4000) {
        void *dir=opendir(source);struct directory_entry *entry;
        if(!dir){mismatch(source,"opendir-source");return;}
        while((entry=readdir(dir))) {
            if(!strcmp(entry->name,".") || !strcmp(entry->name,".."))continue;
            char from[2048],to[2048];
            if(child_path(from,sizeof(from),source,entry->name) || child_path(to,sizeof(to),destination,entry->name)){mismatch(source,"path-length");continue;}
            compare_tree(from,to);
        }
        closedir(dir);dir=opendir(destination);
        if(!dir){mismatch(destination,"opendir-destination");return;}
        while((entry=readdir(dir))) {
            if(!strcmp(entry->name,".") || !strcmp(entry->name,".."))continue;
            char from[2048];struct file_stat extra;
            if(child_path(from,sizeof(from),source,entry->name) || lstat(from,&extra))mismatch(entry->name,"destination-extra");
        }
        closedir(dir);
    } else mismatch(source,"unsupported-file-type");
    if(verified_entries%1000==0){printf("INFERNO_TREE_PROGRESS entries=%llu bytes=%llu mismatches=%llu\n",verified_entries,verified_bytes,mismatches);fflush(0);}
}
/* Mirrors original restored format_effaceable_storage selectors, never raw storage writes. */
static int initialize_effaceable(void) {
    void *io=dlopen("/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit",2);
    void *lib=dlopen("/usr/lib/libSystem.B.dylib",2);
    if(!io || !lib){printf("INFERNO_EFFACEABLE_DLOPEN_FAILED %s\n",dlerror());fflush(0);return -1;}
    void *(*matching)(const char *)=dlsym(io,"IOServiceMatching");
    unsigned (*getservice)(unsigned,void *)=dlsym(io,"IOServiceGetMatchingService");
    int (*serviceopen)(unsigned,unsigned,unsigned,unsigned *)=dlsym(io,"IOServiceOpen");
    int (*scalar)(unsigned,unsigned,const unsigned long long *,unsigned,unsigned long long *,unsigned *)=dlsym(io,"IOConnectCallScalarMethod");
    int (*serviceclose)(unsigned)=dlsym(io,"IOServiceClose");
    int (*release)(unsigned)=dlsym(io,"IOObjectRelease");
    unsigned *task=dlsym(lib,"mach_task_self_");
    if(!matching || !getservice || !serviceopen || !scalar || !serviceclose || !release || !task){printf("INFERNO_EFFACEABLE_DLSYM_FAILED %s\n",dlerror());fflush(0);return -1;}
    unsigned service=getservice(0,matching("AppleEffaceableStorage")),connection=0;
    if(!service)return -1;
    int status=serviceopen(service,*task,0,&connection);
    unsigned long long formatted=0;unsigned count=1;
    if(!status)status=scalar(connection,3,0,0,&formatted,&count);
    printf("INFERNO_EFFACEABLE_QUERY status=%d formatted=%llu count=%u\n",status,formatted,count);fflush(0);
    if(!status && !formatted){
        status=scalar(connection,4,0,0,0,0);
        printf("INFERNO_EFFACEABLE_FORMAT status=%d\n",status);fflush(0);
        if(!status){count=1;status=scalar(connection,3,0,0,&formatted,&count);
            printf("INFERNO_EFFACEABLE_RECHECK status=%d formatted=%llu\n",status,formatted);fflush(0);
            if(!formatted)status=-1;
        }
    }
    if(connection)serviceclose(connection);
    release(service);return status;
}
static void check_fixture_access(const char *context) {
    const char *paths[]={"/mnt2","/mnt2/inferno","/mnt2/inferno/inferno-launcher",0};
    for(unsigned i=0;paths[i];i++){*__error()=0;int status=access(paths[i],1);printf("INFERNO_FIXTURE_ACCESS context=%s path=%s status=%d errno=%d\n",context,paths[i],status,*__error());}
    fflush(0);
}
static void export_owned(const char *path) {
    struct file_stat st;if(lstat(path,&st) || (st.mode&0xf000)!=0x8000)return;
    int fd=open(path,0);if(fd<0)return;
    printf("INFERNO_OWNED_HEX_BEGIN path=%s size=%lld\n",path,st.size);fflush(0);
    unsigned total=0;unsigned char bytes[4096];char hex[8193];const char *digits="0123456789abcdef";
    while(total<131072){long n=read(fd,bytes,sizeof(bytes));if(n<=0)break;for(long i=0;i<n;i++){hex[2*i]=digits[bytes[i]>>4];hex[2*i+1]=digits[bytes[i]&15];}hex[2*n]='\n';write(1,hex,2*n+1);total+=n;}
    close(fd);printf("INFERNO_OWNED_HEX_END bytes=%u complete=%d\n",total,total==(unsigned long long)st.size);fflush(0);
}
static int export_crashes(void) {
    const char *fixture[]={"/mnt2/inferno","/mnt2/inferno/inferno-launcher","/mnt2/inferno/InfernoProbe.app","/mnt2/inferno/InfernoProbe.app/InfernoProbe","/mnt2/inferno/InfernoProbe.app/Info.plist",0};
    for(unsigned i=0;fixture[i];i++) {
        struct file_stat st;int status=lstat(fixture[i],&st);
        printf("INFERNO_POSTBOOT_FIXTURE %s status=%d errno=%d mode=%o uid=%u gid=%u size=%lld\n",fixture[i],status,*__error(),status?0:st.mode,status?0:st.uid,status?0:st.gid,status?-1:st.size);
    }
    fflush(0);
    check_fixture_access("root");
    int child=fork();
    if(child==0){int groups=setgroups(0,0),gid=setgid(501),uid=setuid(501);printf("INFERNO_FIXTURE_IDENTITY groups=%d gid=%d uid=%d\n",groups,gid,uid);check_fixture_access("uid501-gid501");_exit(0);}
    if(child>0){int status;while(waitpid(child,&status,0)<0)if(*__error()!=4)break;}
    struct filesystem_space fs;if(!statfs("/mnt2",&fs))printf("INFERNO_FIXTURE_STATFS flags=%x mounted_from=%s mounted_on=%s\n",fs.flags,fs.mounted_from,fs.mounted_on);
    export_owned("/mnt2/inferno/inferno-launcher");
    export_owned("/mnt2/inferno/InfernoProbe.app/Info.plist");
    const char *directory_path="/mnt2/mobile/Library/Logs/CrashReporter";
    void *directory=opendir(directory_path);if(!directory)return -1;
    struct directory_entry *entry;unsigned long long total=0;unsigned files=0;
    while((entry=readdir(directory)) && total<4194304) {
        size_t n=entry->namelen;
        if(!((n>=4 && !strcmp(entry->name+n-4,".ips")) || (n>=6 && !strcmp(entry->name+n-6,".crash"))))continue;
        char path[2048];if(child_path(path,sizeof(path),directory_path,entry->name))continue;
        struct file_stat st;if(lstat(path,&st) || (st.mode&0xf000)!=0x8000)continue;
        int fd=open(path,0);if(fd<0)continue;
        printf("INFERNO_REPORT_EXPORT_BEGIN name=%s size=%lld limit=524288\n",entry->name,st.size);fflush(0);
        unsigned long long count=0,fnv=14695981039346656037ULL;int error=0;
        char data[4096];
        while(count<524288 && total<4194304) {
            long got=read(fd,data,sizeof(data));if(got<0){error=1;break;}if(!got)break;
            for(long i=0;i<got;i++){fnv^=(unsigned char)data[i];fnv*=1099511628211ULL;}
            long sent=0;while(sent<got){long wrote=write(1,data+sent,got-sent);if(wrote<=0){error=1;break;}sent+=wrote;}
            count+=got;total+=got;if(error)break;
        }
        close(fd);files++;
        printf("\nINFERNO_REPORT_EXPORT_END bytes=%llu fnv1a64=%016llx complete=%d\n",count,fnv,!error && count==(unsigned long long)st.size);fflush(0);
    }
    closedir(directory);
    printf("INFERNO_REPORT_EXPORT_TOTAL files=%u bytes=%llu\n",files,total);fflush(0);return 0;
}
static int ensure(const char *path) {
    if (!mkdir(path, 0755) || *__error() == 17) return 0;
    printf("INFERNO_PREP_MKDIR_FAILED %s errno=%d\n", path, *__error());
    return -1;
}
int main(int argc, char **argv) {
    if (argc < 2 || strcmp(argv[1], "--disposable-root-copy")) return 2;
    int roles = 0, existing = 0, gigalocker = 0, seed_data = 0, copy_sep = 0, verify_data = 0, keybag = 0, readiness = 0, install_cache = 0, export_reports = 0, exec_wrapper = 0, system_launcher = 0, unlock_helper = 0;
    for (int i=2; i<argc; ++i) {
        if (!strcmp(argv[i], "--role-volumes")) roles = 1;
        else if (!strcmp(argv[i], "--existing-volumes")) existing = 1;
        else if (!strcmp(argv[i], "--init-gigalocker")) gigalocker = 1;
        else if (!strcmp(argv[i], "--seed-data")) seed_data = 1;
        else if (!strcmp(argv[i], "--copy-sep")) copy_sep = 1;
        else if (!strcmp(argv[i], "--verify-data")) verify_data = 1;
        else if (!strcmp(argv[i], "--create-keybag")) keybag = 1;
        else if (!strcmp(argv[i], "--install-readiness")) readiness = 1;
        else if (!strcmp(argv[i], "--install-cache")) install_cache = 1;
        else if (!strcmp(argv[i], "--export-reports")) export_reports = 1;
        else if (!strcmp(argv[i], "--install-unlock-helper")) unlock_helper = 1;
        else if (!strcmp(argv[i], "--install-system-launcher")) system_launcher = 1;
        else if (!strcmp(argv[i], "--install-exec-wrapper")) exec_wrapper = 1;
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
    if (seed_data) {
        char *data[] = {"/sbin/newfs_apfs", "-A", "-o", "role=d", "-v", "Data", "/dev/disk0s1", 0};
        char *update[] = {"/sbin/newfs_apfs", "-A", "-o", "role=p", "-v", "Update", "/dev/disk0s1", 0};
        if (run(data) || run(update)) return 15;
    }
    char system_device[64] = {0}, preboot_device[64] = {0}, xart_device[64] = {0}, data_device[64] = {0}, hardware_device[64] = {0};
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
            if (!strcmp(name, "Data")) snprintf(data_device, sizeof(data_device), "%s", device);
            if (!strcmp(name, "Hardware")) snprintf(hardware_device, sizeof(hardware_device), "%s", device);
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
    if (verify_data) {
        if (!data_device[0] || mount_at(system_device, "/mnt1", 1) || mount_at(data_device, "/mnt2", 1)) return 26;
        compare_tree("/mnt1/private/var", "/mnt2");
        int result = mismatches != 0;
        printf("INFERNO_TREE_RESULT entries=%llu files=%llu links=%llu bytes=%llu mismatches=%llu\n", verified_entries,verified_files,verified_links,verified_bytes,mismatches); fflush(0);
        if (unmount("/mnt2", 0) || unmount("/mnt1", 0)) return 27;
        if (result) return 28;
    }
    if (copy_sep) {
        if (mount_at(preboot_device, "/mnt2", 0)) return 23;
        const char *sep = "/mnt2/000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000/usr/standalone/firmware/sep-firmware.img4";
        if (copyfile("/usr/share/inferno-sep-payload", sep, 0, 15 | (1 << 18) | (1 << 19))) {
            printf("INFERNO_SEP_COPY_FAILED errno=%d\n", *__error()); fflush(0); return 24;
        }
        sync();
        if (unmount("/mnt2", 0)) return 25;
        printf("INFERNO_SEP_COPY_COMPLETE: supplied bytes copied to loader path\n"); fflush(0);
    }
    if (seed_data) {
        if (!data_device[0] || !hardware_device[0]) return 16;
        if (mount_at(system_device, "/mnt1", 1) || mount_at(data_device, "/mnt2", 0)) return 17;
        if (space("/mnt2", "before-data-seed") || copy_contents("/mnt1/private/var", "/mnt2") || space("/mnt2", "after-data-seed")) return 18;
        if (ensure("/mnt4") || mount_at(hardware_device, "/mnt4", 0)) return 19;
        const char *dirs[] = {"/mnt4/FactoryData", "/mnt4/FactoryData/System", "/mnt4/FactoryData/System/Library", "/mnt4/FactoryData/System/Library/Caches", "/mnt4/FactoryData/System/Library/Caches/com.apple.factorydata", 0};
        for (int i=0; dirs[i]; ++i) if (ensure(dirs[i])) return 20;
        if (!access("/mnt1/System/Library/Caches/com.apple.factorydata", 0) &&
            copy_contents("/mnt1/System/Library/Caches/com.apple.factorydata", dirs[4])) return 21;
        sync();
        if (unmount("/mnt4", 0) || unmount("/mnt2", 0) || unmount("/mnt1", 0)) return 22;
        printf("INFERNO_DATA_COMPLETE: original var seeded; Update and Hardware mount paths prepared\n"); fflush(0);
    }
    if (gigalocker) {
        if (!xart_device[0] || ensure("/mnt7") || mount_at(xart_device, "/mnt7", 0)) return 12;
        char *init[] = {"/usr/libexec/seputil", "--gigalocker-init", 0};
        if (run(init)) return 13;
        sync();
        if (unmount("/mnt7", 0)) return 14;
        printf("INFERNO_GIGALOCKER_COMPLETE: original seputil initialization and clean unmount succeeded\n"); fflush(0);
    }
    if(readiness) {
        if(mount_at(system_device,"/mnt1",0))return 37;
        if(copyfile("/usr/share/inferno-readiness","/mnt1/usr/bin/inferno-readiness",0,15) ||
           copyfile("/usr/share/org.inferno.readiness.plist","/mnt1/System/Library/LaunchDaemons/org.inferno.readiness.plist",0,15))return 38;
        sync();if(unmount("/mnt1",0))return 39;
        printf("INFERNO_READINESS_INSTALLED\n");fflush(0);
    }
    if(exec_wrapper) {
        if(mount_at(system_device,"/mnt1",0))return 47;
        if(copyfile("/usr/share/inferno-exec-launcher","/mnt1/usr/bin/inferno-exec-launcher",0,15))return 48;
        unsigned long long prior_bytes=verified_bytes;
        compare_tree("/usr/share/inferno-exec-launcher","/mnt1/usr/bin/inferno-exec-launcher");
        printf("INFERNO_EXEC_WRAPPER_READBACK bytes=%llu mismatches=%llu\n",verified_bytes-prior_bytes,mismatches);fflush(0);
        sync();if(unmount("/mnt1",0))return 49;if(mismatches)return 50;
    }
    if(system_launcher) {
        if(mount_at(system_device,"/mnt1",0))return 51;
        if(copyfile("/usr/share/inferno-system-launcher","/mnt1/usr/bin/inferno-launcher",0,15))return 52;
        unsigned long long prior_bytes=verified_bytes;
        compare_tree("/usr/share/inferno-system-launcher","/mnt1/usr/bin/inferno-launcher");
        printf("INFERNO_SYSTEM_LAUNCHER_READBACK bytes=%llu mismatches=%llu\n",verified_bytes-prior_bytes,mismatches);fflush(0);
        sync();if(unmount("/mnt1",0))return 53;if(mismatches)return 54;
    }
    if(unlock_helper) {
        if(mount_at(system_device,"/mnt1",0))return 55;
        if(copyfile("/usr/share/inferno-unlock-empty","/mnt1/usr/bin/inferno-unlock-empty",0,15))return 56;
        unsigned long long prior_bytes=verified_bytes;
        compare_tree("/usr/share/inferno-unlock-empty","/mnt1/usr/bin/inferno-unlock-empty");
        printf("INFERNO_UNLOCK_HELPER_READBACK bytes=%llu mismatches=%llu\n",verified_bytes-prior_bytes,mismatches);fflush(0);
        sync();if(unmount("/mnt1",0))return 57;if(mismatches)return 58;
    }
    if(install_cache) {
        if(mount_at(system_device,"/mnt1",0))return 40;
        if(copyfile("/usr/share/inferno-launchd-cache.plist","/mnt1/System/Library/xpc/launchd.plist",0,15))return 41;
        unsigned long long prior_bytes=verified_bytes;
        compare_tree("/usr/share/inferno-launchd-cache.plist","/mnt1/System/Library/xpc/launchd.plist");
        printf("INFERNO_CACHE_READBACK bytes=%llu mismatches=%llu\n",verified_bytes-prior_bytes,mismatches);fflush(0);
        sync();if(unmount("/mnt1",0))return 42;
        if(mismatches)return 43;
        printf("INFERNO_LAUNCHD_CACHE_INSTALLED: explicit configuration only; signature unchanged\n");fflush(0);
    }
    if(export_reports) {
        if(!data_device[0] || mount_at(data_device,"/mnt2",1))return 44;
        int result=export_crashes();if(unmount("/mnt2",0))return 45;if(result)return 46;
    }
    if (keybag) {
        if (!xart_device[0] || !data_device[0] || ensure("/mnt7") ||
            mount_at(xart_device,"/mnt7",0) || mount_at(preboot_device,"/mnt1",1) || mount_at(data_device,"/mnt2",0)) return 29;
        char *init[] = {"/usr/libexec/seputil", "--gigalocker-init", 0};
        char *load[] = {"/usr/libexec/seputil", "--wait", "--load", "/mnt1/000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000/usr/standalone/firmware/sep-firmware.img4", 0};
        if(run(init) || run(load))return 30;
        if(initialize_effaceable())return 36;
        void *framework=dlopen("/System/Library/PrivateFrameworks/MobileKeyBag.framework/MobileKeyBag",2);
        if(!framework){printf("INFERNO_KEYBAG_DLOPEN_FAILED %s\n",dlerror());fflush(0);return 31;}
        /* Original restored_external uses NULL secret and /mnt2; no generated blob in owned code. */
        int (*create)(void *,const char *)=(int (*)(void *,const char *))dlsym(framework,"MKBKeyBagCreateSystem");
        if(!create){printf("INFERNO_KEYBAG_DLSYM_FAILED %s\n",dlerror());fflush(0);return 32;}
        printf("INFERNO_KEYBAG_CREATE_BEGIN\n");fflush(0);
        int status=create(0,"/mnt2");struct file_stat bag;
        int stat_status=lstat("/mnt2/keybags/systembag.kb",&bag);
        printf("INFERNO_KEYBAG_CREATE_RESULT status=%d stat=%d size=%lld mode=%o\n",status,stat_status,stat_status?-1:bag.size,stat_status?0:bag.mode);fflush(0);
        char *shutdown[] = {"/usr/libexec/seputil", "--gigalocker-shutdown", 0};
        if(run(shutdown))return 35;
        sync();
        if(unmount("/mnt2",0) || unmount("/mnt1",0) || unmount("/mnt7",0))return 33;
        if((status && status!=-4) || stat_status || bag.size<=0)return 34;
        printf("INFERNO_KEYBAG_COMPLETE: original framework created or found system keybag\n");fflush(0);
    }
    printf("INFERNO_PREP_COMPLETE: requested preparation operations succeeded\n"); fflush(0);
    return 0;
}
