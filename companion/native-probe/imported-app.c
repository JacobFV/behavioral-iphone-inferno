/* Included by prepare-root.c; fixed host-validated plan, no original API patches. */
struct imported_header {
    char magic[8]; uint32_t count, allow_identical_fixture;
    unsigned long long bytes; char bundle[128], identifier[256];
};
struct imported_entry { char path[512]; uint32_t mode, type; unsigned long long bytes; };
_Static_assert(sizeof(struct imported_header)==408,"owned plan header ABI");
_Static_assert(sizeof(struct imported_entry)==528,"owned plan entry ABI");
static struct imported_header imported;
static struct imported_entry imported_entries[4096];
static int imported_path(const char *s, unsigned capacity, int components) {
    unsigned start=0, depth=1;
    for(unsigned i=0;i<capacity;i++) {
        char c=s[i];
        if(!c || c=='/') {
            if(i==start || (i-start==1 && s[start]=='.') || (i-start==2 && s[start]=='.' && s[start+1]=='.'))return -1;
            if(!c)return (int)i;
            if(!components || ++depth>16)return -1;
            start=i+1;
        } else if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'||c==' '))return -1;
    }
    return -1;
}
static int imported_read(int fd,void *buffer,size_t bytes) {
    unsigned char *p=buffer;
    while(bytes) {long n=read(fd,p,bytes);if(n<0 && *__error()==4)continue;if(n<=0)return -1;p+=n;bytes-=n;}
    return 0;
}
static int imported_count_tree(const char *path,unsigned depth,unsigned *count,unsigned long long *bytes) {
    if(depth>16)return -1;
    void *dir=opendir(path);if(!dir)return -1;
    int result=0;struct directory_entry *entry;
    while((entry=readdir(dir))) {
        if(!strcmp(entry->name,".")||!strcmp(entry->name,".."))continue;
        char child[2048];struct file_stat st;
        if(++*count>4096 || child_path(child,sizeof(child),path,entry->name) || lstat(child,&st) || st.uid || st.gid) {result=-1;break;}
        unsigned type=st.mode&0170000;
        if(type==0040000) {if(imported_count_tree(child,depth+1,count,bytes)){result=-1;break;}}
        else if(type==0100000 && st.nlink==1 && st.size>=0) {*bytes+=st.size;if(*bytes>134217728){result=-1;break;}}
        else {result=-1;break;}
    }
    closedir(dir);return result;
}
static int imported_plan(void) {
    const char *source="/usr/share/inferno-imported-app";
    struct file_stat st;int fd=open("/usr/share/inferno-imported-app.plan",0x100); /* O_NOFOLLOW */
    if(fd<0)return -1;
    int result=imported_read(fd,&imported,sizeof(imported));
    if(!result) {
        for(int i=0;i<8;i++)if(imported.magic[i]!="IFAPP001"[i])result=-1;
        int length=imported_path(imported.bundle,sizeof(imported.bundle),0);
        if(length<5 || strcmp(imported.bundle+length-4,".app") || imported_path(imported.identifier,sizeof(imported.identifier),0)<0 || !imported.count || imported.count>4096 || imported.bytes>134217728 || imported.allow_identical_fixture>1)result=-1;
        if(!result && imported_read(fd,imported_entries,imported.count*sizeof(imported_entries[0])))result=-1;
        unsigned char extra;if(!result && read(fd,&extra,1)!=0)result=-1;
    }
    close(fd);if(result)return result;
    if(lstat(source,&st) || st.mode!=0040755 || st.uid || st.gid)return -1;
    unsigned long long bytes=0;unsigned files=0;
    for(unsigned i=0;i<imported.count;i++) {
        struct imported_entry *e=&imported_entries[i];char path[2048];
        if(imported_path(e->path,sizeof(e->path),1)<0 || child_path(path,sizeof(path),source,e->path) || lstat(path,&st))return -1;
        for(unsigned j=0;j<i;j++)if(!strcmp(e->path,imported_entries[j].path))return -1;
        if(e->type==1) {if(e->mode!=0755 || e->bytes || st.mode!=0040755)return -1;}
        else if(e->type==2) {if((e->mode!=0644 && e->mode!=0755) || st.mode!=(0100000|e->mode) || st.nlink!=1 || st.size<0 || (unsigned long long)st.size!=e->bytes || e->bytes>67108864)return -1;bytes+=e->bytes;files++;}
        else return -1;
        if(st.uid || st.gid)return -1;
    }
    unsigned count=0;unsigned long long walked_bytes=0;
    if(imported_count_tree(source,0,&count,&walked_bytes) || count!=imported.count || bytes!=imported.bytes || walked_bytes!=bytes || !files)return -1;
    if(imported.allow_identical_fixture && (strcmp(imported.bundle,"InfernoProbe.app") || strcmp(imported.identifier,"org.inferno.companion.probe") || imported.count!=2 || files!=2))return -1;
    printf("INFERNO_IMPORTED_APP_PLAN bundle=%s identifier=%s entries=%u bytes=%llu identical_fixture=%u\n",imported.bundle,imported.identifier,imported.count,bytes,imported.allow_identical_fixture);fflush(0);return 0;
}
/* Only newly created owned directories: preserve source metadata like copy_contents.
 * Never applied to /Applications or an existing collision target. */
static int imported_directory_metadata(const char *source,const char *target) {
    struct file_stat a,b;int sa=lstat(source,&a),sb=lstat(target,&b);
    printf("INFERNO_IMPORTED_APP_DIR_METADATA_BEFORE target=%s source_stat=%d source_mode=%o source_uid=%u source_gid=%u target_stat=%d target_mode=%o target_uid=%u target_gid=%u\n",
           target,sa,sa?0:a.mode,sa?0:a.uid,sa?0:a.gid,sb,sb?0:b.mode,sb?0:b.uid,sb?0:b.gid);fflush(0);
    if(sa || sb || a.mode!=0040755 || a.uid || a.gid || (b.mode&0170000)!=0040000)return -1;
    int copied=copyfile(source,target,0,7 | (1 << 18) | (1 << 19));
    int copy_errno=copied?*__error():0;
    int after=lstat(target,&b);
    printf("INFERNO_IMPORTED_APP_DIR_METADATA_AFTER target=%s copy=%d copy_errno=%d stat=%d mode=%o uid=%u gid=%u\n",
           target,copied,copy_errno,after,after?0:b.mode,after?0:b.uid,after?0:b.gid);fflush(0);
    return copied || after || a.mode!=b.mode || a.uid!=b.uid || a.gid!=b.gid ? -1:0;
}
static int install_imported_app(const char *system_device) {
    if(imported_plan())return 80;
    if(mount_at(system_device,"/mnt1",0))return 81;
    const char *source="/usr/share/inferno-imported-app";char target[2048];struct file_stat st;int result=0;
    int parent_stat=lstat("/mnt1/Applications",&st);
    int parent_errno=parent_stat?*__error():0;
    int target_path=child_path(target,sizeof(target),"/mnt1/Applications",imported.bundle);
    printf("INFERNO_IMPORTED_APP_PARENT stat=%d errno=%d mode=%o uid=%u gid=%u nlink=%u path_result=%d\n",
           parent_stat,parent_errno,parent_stat?0:st.mode,parent_stat?0:st.uid,
           parent_stat?0:st.gid,parent_stat?0:st.nlink,target_path);fflush(0);
    if(!parent_stat && (st.mode&0170000)==0120000) {
        char link[512];long length=readlink("/mnt1/Applications",link,sizeof(link)-1);
        if(length>=0 && length<(long)sizeof(link)-1) {link[length]=0;printf("INFERNO_IMPORTED_APP_PARENT_LINK bytes=%ld target=%s\n",length,link);}
        else printf("INFERNO_IMPORTED_APP_PARENT_LINK bytes=%ld errno=%d truncated_or_failed=1\n",length,length<0?*__error():0);
        fflush(0);
    }
    /* Actual original System parent is root:admin 0775 (diagnostic stage 2).
     * Keep the prior ordinary root:wheel 0755 case; do not rewrite the parent.
     * Exact full modes reject links, special bits and world-write permission.
     * Link count is diagnostic: it changes normally as applications are added. */
    int parent_allowed=!parent_stat && !st.uid &&
        ((st.mode==0040775 && st.gid==80) || (st.mode==0040755 && st.gid==0));
    if(!parent_allowed || target_path)result=82;
    if(!result) {
        if(!lstat(target,&st)) {
            if(!imported.allow_identical_fixture || st.mode!=0040755 || st.uid || st.gid)result=83;
            else {unsigned count=0;unsigned long long bytes=0;if(imported_count_tree(target,0,&count,&bytes) || count!=imported.count || bytes!=imported.bytes)result=84;else compare_tree(source,target);if(mismatches)result=84;if(!result)printf("INFERNO_IMPORTED_APP_IDENTICAL_COLLISION_ACCEPTED\n");}
        } else if(*__error()!=2 || mkdir(target,0755))result=85;
        else if(imported_directory_metadata(source,target))result=92;
    }
    if(!result)for(unsigned i=0;i<imported.count;i++) {
        struct imported_entry *e=&imported_entries[i];char from[2048],to[2048];
        if(child_path(from,sizeof(from),source,e->path)||child_path(to,sizeof(to),target,e->path)){result=86;break;}
        if(e->type==1) {if(mkdir(to,0755)){result=87;break;}if(imported_directory_metadata(from,to)){result=92;break;}}
        else if(copyfile(from,to,0,15)){result=88;break;}
    }
    if(!result) {
        unsigned long long before=verified_bytes;compare_tree(source,target);
        printf("INFERNO_IMPORTED_APP_READBACK bundle=%s bytes=%llu entries=%u mismatches=%llu\n",imported.bundle,verified_bytes-before,imported.count,mismatches);fflush(0);
        if(mismatches)result=89;
    }
    sync();int unmounted=unmount("/mnt1",0);
    printf("INFERNO_IMPORTED_APP_FINISH result=%d unmount=%d errno=%d\n",result,unmounted,unmounted?*__error():0);fflush(0);
    return unmounted?90:result;
}
