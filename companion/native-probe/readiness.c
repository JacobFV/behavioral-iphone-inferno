/* Owned observation-only helper; original guest ps supplies process listing. */
extern int printf(const char *, ...), fflush(void *), fork(void), waitpid(int,int *,int);
extern int execve(const char *,char *const[],char *const[]), *__error(void);
extern void _exit(int);
extern unsigned sleep(unsigned);
extern int snprintf(char *,unsigned long,const char *,...),open(const char *,int,...),close(int),strcmp(const char *,const char *);
extern long read(int,void *,unsigned long),write(int,const void *,unsigned long);
struct file_stat { int dev;unsigned short mode,nlink;unsigned long long ino;unsigned uid,gid;int rdev;long long times[8],size,blocks;int blksize;unsigned flags,gen;int spare;long long qspare[2]; };
extern int lstat(const char *,struct file_stat *);
_Static_assert(sizeof(struct file_stat)==144,"Darwin stat ABI");
static unsigned report_count;
static char reported[8][2048];
static int suffix(const char *name,const char *end) {
    unsigned n=0,m=0;while(name[n])n++;while(end[m])m++;
    return n>=m && !strcmp(name+n-m,end);
}
static void report_prefix(const char *directory,const char *name) {
    if(report_count>=8 || (!suffix(name,".ips") && !suffix(name,".crash")))return;
    char path[2048];int n=snprintf(path,sizeof(path),"%s/%s",directory,name);
    if(n<0 || n>=sizeof(path))return;
    for(unsigned i=0;i<report_count;i++)if(!strcmp(path,reported[i]))return;
    struct file_stat st;if(lstat(path,&st) || (st.mode&0xf000)!=0x8000)return;
    int fd=open(path,0);if(fd<0)return;
    snprintf(reported[report_count++],2048,"%s",path);
    printf("INFERNO_CRASH_PREFIX_BEGIN %s size=%lld limit=32768\n",path,st.size);fflush(0);
    char buffer[4096];unsigned total=0;
    while(total<32768) {
        long got=read(fd,buffer,sizeof(buffer));if(got<=0)break;
        for(long i=0;i<got;i++)if((unsigned char)buffer[i]<32 && buffer[i]!='\n' && buffer[i]!='\r' && buffer[i]!='\t')buffer[i]='.';
        write(1,buffer,got);total+=got;
    }
    close(fd);printf("\nINFERNO_CRASH_PREFIX_END bytes=%u\n",total);fflush(0);
}
struct entry { unsigned long long inode,seek; unsigned short length,namelen; unsigned char type; char name[1024]; };
extern void *opendir(const char *);
extern struct entry *readdir(void *);
extern int closedir(void *);
static void fixture_inventory(void) {
    const char *paths[]={"/var","/private/var","/private/var/inferno","/private/var/inferno/inferno-launcher","/private/var/inferno/InfernoProbe.app","/private/var/inferno/InfernoProbe.app/InfernoProbe","/var/inferno/inferno-launcher",0};
    for(unsigned i=0;paths[i];i++) {
        struct file_stat st;int status=lstat(paths[i],&st);
        printf("INFERNO_FIXTURE_STAT %s result=%d errno=%d mode=%o uid=%u gid=%u size=%lld\n",paths[i],status,*__error(),status?0:st.mode,status?0:st.uid,status?0:st.gid,status?-1:st.size);
    }
    fflush(0);
}
static void crash_inventory(void) {
    const char *paths[]={"/private/var/mobile/Library/Logs/CrashReporter","/private/var/logs/CrashReporter","/private/var/log",0};
    for(unsigned i=0;paths[i];i++) {
        void *directory=opendir(paths[i]);
        printf("INFERNO_LOG_DIRECTORY %s opened=%d errno=%d\n",paths[i],directory!=0,*__error());
        if(!directory)continue;
        struct entry *e;unsigned count=0;
        while((e=readdir(directory)) && count++<100){printf("INFERNO_LOG_ENTRY %s/%s type=%u\n",paths[i],e->name,e->type);if(i<2)report_prefix(paths[i],e->name);}
        closedir(directory);
    }
    fflush(0);
}
int main(void) {
    const unsigned delay[]={15,30,45,60};
    unsigned elapsed=0;
    for(unsigned i=0;i<4;i++) {
        sleep(delay[i]);elapsed+=delay[i];
        printf("INFERNO_READINESS_BEGIN seconds=%u\n",elapsed);fflush(0);
        int pid=fork();
        if(pid==0){
            char *args[]={"/bin/ps","-A","-ww","-o","pid,ppid,state,comm",0};
            char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin",0};
            execve(args[0],args,env);_exit(127);
        }
        int status=-1;
        if(pid>0)while(waitpid(pid,&status,0)<0)if(*__error()!=4)break;
        printf("INFERNO_READINESS_END seconds=%u status=%d\n",elapsed,status);fflush(0);
        fixture_inventory();
        crash_inventory();
    }
    return 0;
}
