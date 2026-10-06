/* Owned, observation-only IOService snapshot. No property access or user client. */
typedef unsigned io_object_t;
typedef unsigned long long registry_id_t;
extern void *IOServiceMatching(const char *),*IOServiceNameMatching(const char *);
extern int IOServiceGetMatchingServices(unsigned,const void *,io_object_t *);
extern io_object_t IOIteratorNext(io_object_t);
extern int IOObjectRelease(io_object_t),IOObjectGetClass(io_object_t,char *);
extern unsigned IOObjectConformsTo(io_object_t,const char *);
extern int IORegistryEntryGetName(io_object_t,char *);
extern int IORegistryEntryGetRegistryEntryID(io_object_t,registry_id_t *);
extern int IORegistryEntryGetParentIterator(io_object_t,const char *,io_object_t *);
extern int IORegistryEntryGetChildIterator(io_object_t,const char *,io_object_t *);
extern int IOServiceGetBusyState(io_object_t,unsigned *);
extern int printf(const char *,...),fflush(void *);
extern long write(int,const void *,unsigned long);
extern unsigned alarm(unsigned);
_Static_assert(sizeof(io_object_t)==4,"Darwin Mach port width");
_Static_assert(sizeof(registry_id_t)==8,"Darwin registry ID width");
static unsigned nodes;
static void clean(char s[128]) {
    s[127]=0;
    for(unsigned i=0;s[i];i++)if((unsigned char)s[i]<33 || (unsigned char)s[i]>126)s[i]='_';
}
static void entry(io_object_t object,const char *relation,registry_id_t anchor) {
    char name[128]={0},klass[128]={0};registry_id_t id=0;unsigned busy=0;
    int nr=IORegistryEntryGetName(object,name),cr=IOObjectGetClass(object,klass);
    int ir=IORegistryEntryGetRegistryEntryID(object,&id);
    unsigned service=IOObjectConformsTo(object,"IOService");
    int br=service?IOServiceGetBusyState(object,&busy):-1;
    clean(name);clean(klass);nodes++;
    printf("INFERNO_IOREG_NODE relation=%s anchor=%llu id=%llu id_status=0x%x name=%s name_status=0x%x class=%s class_status=0x%x is_service=%u busy=%u busy_status=0x%x\n",relation,anchor,id,ir,name,nr,klass,cr,service,busy,br);
    fflush(0);
}
static void adjacent(io_object_t object,registry_id_t anchor,int parent) {
    io_object_t iterator=0;
    int r=parent?IORegistryEntryGetParentIterator(object,"IOService",&iterator):IORegistryEntryGetChildIterator(object,"IOService",&iterator);
    const char *relation=parent?"parent":"child";
    printf("INFERNO_IOREG_ITER relation=%s anchor=%llu status=0x%x\n",relation,anchor,r);fflush(0);
    if(r || !iterator)return;
    unsigned count=0;io_object_t item;
    while(count<16 && nodes<128 && (item=IOIteratorNext(iterator))) {
        entry(item,relation,anchor);IOObjectRelease(item);count++;
    }
    printf("INFERNO_IOREG_ITER_END relation=%s anchor=%llu count=%u limit_reached=%u\n",relation,anchor,count,count==16 || nodes==128);fflush(0);
    IOObjectRelease(iterator);
}
static int snapshot(void *matching,const char *kind,const char *query) {
    if(!matching){printf("INFERNO_IOREG_ERROR matching-null kind=%s query=%s\n",kind,query);fflush(0);return 2;}
    io_object_t iterator=0;
    /* GetMatchingServices consumes its matching dictionary, including on error. */
    int r=IOServiceGetMatchingServices(0,matching,&iterator);
    printf("INFERNO_IOREG_MATCH kind=%s query=%s status=0x%x\n",kind,query,r);fflush(0);
    if(r || !iterator)return 3;
    unsigned matches=0;io_object_t object;
    while(matches<8 && nodes<128 && (object=IOIteratorNext(iterator))) {
        registry_id_t anchor=0;IORegistryEntryGetRegistryEntryID(object,&anchor);
        entry(object,"match",anchor);adjacent(object,anchor,1);adjacent(object,anchor,0);
        IOObjectRelease(object);matches++;
    }
    IOObjectRelease(iterator);
    printf("INFERNO_IOREG_MATCH_END kind=%s query=%s matches=%u limit_reached=%u\n",kind,query,matches,matches==8 || nodes==128);fflush(0);
    return 0;
}
int inferno_ioreg_touch_snapshot(void) {
    nodes=0;
    static const char begin[]="INFERNO_IOREG_BEGIN max_matches=8 max_adjacent=16 max_nodes=128 watchdog=600\n";
    write(1,begin,sizeof(begin)-1);alarm(600);
    int gpio=snapshot(IOServiceNameMatching("aop-gpio"),"name","aop-gpio");
    int touch=snapshot(IOServiceMatching("AppleHIDTransportDeviceSPI"),"class","AppleHIDTransportDeviceSPI");
    alarm(0);
    printf("INFERNO_IOREG_COMPLETE nodes=%u gpio_status=%d touch_status=%d limit_reached=%u\n",nodes,gpio,touch,nodes==128);fflush(0);
    return gpio || touch ? 4:0;
}

#ifndef IOREG_TOUCH_LIBRARY
int main(void) { return inferno_ioreg_touch_snapshot(); }
#endif
