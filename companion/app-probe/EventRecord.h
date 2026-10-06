// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned fixed-path event protocol; no SDK implementation.
#ifndef INFERNO_EVENT_RECORD_H
#define INFERNO_EVENT_RECORD_H
#define INFERNO_EVENT_PATH "/var/mobile/Library/Caches/org.inferno.companion.probe.events"
#define INFERNO_EVENT_LIMIT 16384
extern int sysctlbyname(const char *,void *,unsigned long *,void *,unsigned long);
extern int strcmp(const char *,const char *);
struct inferno_event_stat { int dev;unsigned short mode,nlink;unsigned long long ino;unsigned uid,gid;int rdev;long long times[8],size,blocks;int blksize;unsigned flags,gen;int spare;long long qspare[2]; };
_Static_assert(sizeof(struct inferno_event_stat)==144,"Darwin stat ABI");
extern int fstat(int,struct inferno_event_stat *);
static int inferno_boot_uuid(char out[37]) {
    unsigned long n=37;
    if(sysctlbyname("kern.bootsessionuuid",out,&n,0,0) || n!=37 || out[36])return -1;
    unsigned nonzero=0;
    for(unsigned i=0;i<36;i++) {
        char c=out[i];
        if(i==8 || i==13 || i==18 || i==23) {if(c!='-')return -1;}
        else if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')||(c>='A'&&c<='F')))return -1;
        if(c!='0' && c!='-')nonzero=1;
    }
    return nonzero?0:-1;
}
static int inferno_event_name(const char *s) {
    return !strcmp(s,"main") || !strcmp(s,"view-loaded") || !strcmp(s,"appeared") ||
           !strcmp(s,"tap") || !strcmp(s,"window-visible-requested") || !strcmp(s,"active");
}
#endif
