/* Owned diagnostic for the VM keybag created with MKBKeyBagCreateSystem(NULL).
 * Uses original MobileKeyBag API; no key material, synthetic notification or
 * policy modification. A process makes at most one empty-passcode attempt. */
extern void *dlopen(const char *,int), *dlsym(void *,const char *);
extern char *dlerror(void);
extern int printf(const char *,...),fflush(void *);
extern unsigned sleep(unsigned);
int main(void) {
    sleep(30);
    void *framework=dlopen("/System/Library/PrivateFrameworks/MobileKeyBag.framework/MobileKeyBag",2);
    if(!framework){printf("INFERNO_UNLOCK_DLOPEN_FAILED %s\n",dlerror());fflush(0);return 2;}
    int (*state)(void *)=dlsym(framework,"MKBGetDeviceLockState");
    int (*ever)(void)=dlsym(framework,"MKBDeviceUnlockedSinceBoot");
    int (*unlock)(void *,void *)=dlsym(framework,"MKBUnlockDevice");
    if(!state||!ever||!unlock){printf("INFERNO_UNLOCK_SYMBOL_FAILED\n");fflush(0);return 3;}
    int before=state(0),first=ever();
    printf("INFERNO_UNLOCK_BEFORE state=%d unlocked_since_boot=%d\n",before,first);fflush(0);
    if(first<0){printf("INFERNO_UNLOCK_SKIPPED reason=query-error\n");fflush(0);return 4;}
    if(first){printf("INFERNO_UNLOCK_SKIPPED reason=already-unlocked\n");fflush(0);return 0;}
    int result=unlock(0,0);
    printf("INFERNO_UNLOCK_SINGLE_EMPTY_ATTEMPT result=%d\n",result);fflush(0);
    int after=state(0),unlocked=ever();
    printf("INFERNO_UNLOCK_AFTER state=%d unlocked_since_boot=%d\n",after,unlocked);fflush(0);
    return result || unlocked<=0 ? 5 : 0;
}
