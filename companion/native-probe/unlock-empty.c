/* Owned diagnostic for the VM keybag created with MKBKeyBagCreateSystem(NULL).
 * Uses original MobileKeyBag API; no key material, synthetic notification or
 * policy modification. A process makes at most one empty-passcode attempt. */
extern void *dlopen(const char *,int), *dlsym(void *,const char *);
extern char *dlerror(void);
extern int printf(const char *,...),fflush(void *);
extern unsigned sleep(unsigned),alarm(unsigned);
extern long write(int,const void *,unsigned long);
extern int access(const char *,int), *__error(void);
static void mark(const char *text) { unsigned long n=0;while(text[n])n++;write(1,text,n); }
static void data_access(const char *phase) {
    *__error()=0;int result=access("/private/var/inferno/inferno-launcher",1);int error=*__error();
    printf("INFERNO_UNLOCK_DATA_ACCESS phase=%s result=%d errno=%d\n",phase,result,error);fflush(0);
}
int main(void) {
    static const char begin[]="INFERNO_UNLOCK_BEGIN watchdog=120 maximum_attempts=1\n";
    write(1,begin,sizeof(begin)-1);alarm(120);
    sleep(30);
    mark("INFERNO_UNLOCK_STAGE dlopen\n");
    void *framework=dlopen("/System/Library/PrivateFrameworks/MobileKeyBag.framework/MobileKeyBag",2);
    if(!framework){printf("INFERNO_UNLOCK_DLOPEN_FAILED %s\n",dlerror());fflush(0);return 2;}
    mark("INFERNO_UNLOCK_STAGE resolve-symbols\n");
    int (*state)(void *)=dlsym(framework,"MKBGetDeviceLockState");
    int (*ever)(void)=dlsym(framework,"MKBDeviceUnlockedSinceBoot");
    int (*unlock)(void *,void *)=dlsym(framework,"MKBUnlockDevice");
    if(!state||!ever||!unlock){printf("INFERNO_UNLOCK_SYMBOL_FAILED\n");fflush(0);return 3;}
    mark("INFERNO_UNLOCK_STAGE query-state-before\n");
    int before=state(0);
    mark("INFERNO_UNLOCK_STAGE query-first-before\n");
    int first=ever();
    printf("INFERNO_UNLOCK_BEFORE state=%d unlocked_since_boot=%d\n",before,first);fflush(0);
    if(first<0){printf("INFERNO_UNLOCK_SKIPPED reason=query-error\n");fflush(0);return 4;}
    if(first){printf("INFERNO_UNLOCK_SKIPPED reason=already-unlocked\n");fflush(0);return 0;}
    mark("INFERNO_UNLOCK_STAGE access-before\n");data_access("before");
    mark("INFERNO_UNLOCK_STAGE single-empty-attempt\n");
    int result=unlock(0,0);
    printf("INFERNO_UNLOCK_SINGLE_EMPTY_ATTEMPT result=%d\n",result);fflush(0);
    mark("INFERNO_UNLOCK_STAGE query-state-after\n");
    int after=state(0);
    mark("INFERNO_UNLOCK_STAGE query-first-after\n");
    int unlocked=ever();
    mark("INFERNO_UNLOCK_STAGE access-after\n");
    data_access("after");
    printf("INFERNO_UNLOCK_AFTER state=%d unlocked_since_boot=%d\n",after,unlocked);fflush(0);
    return result || unlocked<=0 ? 5 : 0;
}
