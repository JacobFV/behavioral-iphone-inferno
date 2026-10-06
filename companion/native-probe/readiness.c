/* Owned observation-only helper; original guest ps supplies process listing. */
extern int printf(const char *, ...), fflush(void *), fork(void), waitpid(int,int *,int);
extern int execve(const char *,char *const[],char *const[]), *__error(void);
extern void _exit(int);
extern unsigned sleep(unsigned);
struct entry { unsigned long long inode,seek; unsigned short length,namelen; unsigned char type; char name[1024]; };
extern void *opendir(const char *);
extern struct entry *readdir(void *);
extern int closedir(void *);
static void crash_inventory(void) {
    const char *paths[]={"/private/var/mobile/Library/Logs/CrashReporter","/private/var/logs/CrashReporter","/private/var/log",0};
    for(unsigned i=0;paths[i];i++) {
        void *directory=opendir(paths[i]);
        printf("INFERNO_LOG_DIRECTORY %s opened=%d errno=%d\n",paths[i],directory!=0,*__error());
        if(!directory)continue;
        struct entry *e;unsigned count=0;
        while((e=readdir(directory)) && count++<100)printf("INFERNO_LOG_ENTRY %s/%s type=%u\n",paths[i],e->name,e->type);
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
        crash_inventory();
    }
    return 0;
}
