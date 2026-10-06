/* Owned standard HID touchscreen, through original IOHIDUserDevice APIs. */
#include "hid-input.h"
extern void *dlopen(const char *,int),*dlsym(void *,const char *);
extern int printf(const char *,...),fflush(void *),usleep(unsigned);
extern unsigned long long mach_absolute_time(void);
extern unsigned mach_task_self_;
typedef void *Object;
static Object device;
static Object (*dictionary)(Object,long,const void *,const void *);
static void (*set)(Object,Object,Object),(*release)(Object);
static Object (*string)(Object,const char *,unsigned),(*data)(Object,const unsigned char *,long);
static Object (*create)(Object,Object);
static int (*report)(Object,unsigned long long,const unsigned char *,long);
static unsigned (*copy_service)(Object);
static int (*registry_id)(unsigned,unsigned long long *),(*object_release)(unsigned),(*iterator_create)(unsigned,const char *,unsigned,unsigned *),(*conforms)(unsigned,const char *),(*object_class)(unsigned,char *),(*children)(unsigned,const char *,unsigned *);
static unsigned (*iterator_next)(unsigned);
static Object (*service_matching)(const char *);
static unsigned (*matching_service)(unsigned,Object);
static int (*service_open)(unsigned,unsigned,unsigned,unsigned *),(*service_close)(unsigned);
static int descriptor_parser_exported;
static const void *key_callbacks,*value_callbacks;
static Object true_value;
static Object (*copy_property)(unsigned,Object,Object,unsigned);
static unsigned long (*type_id)(Object),(*boolean_type)(void),(*number_type)(void),(*string_type)(void);
static unsigned char (*boolean_value)(Object),(*number_value)(Object,int,void *),(*string_value)(Object,char *,long,unsigned);
static void diagnostic_symbols(void *cf,void *io) {
    *(void **)(&copy_property)=dlsym(io,"IORegistryEntryCreateCFProperty");
    *(void **)(&type_id)=dlsym(cf,"CFGetTypeID");
    *(void **)(&boolean_type)=dlsym(cf,"CFBooleanGetTypeID");
    *(void **)(&number_type)=dlsym(cf,"CFNumberGetTypeID");
    *(void **)(&string_type)=dlsym(cf,"CFStringGetTypeID");
    *(void **)(&boolean_value)=dlsym(cf,"CFBooleanGetValue");
    *(void **)(&number_value)=dlsym(cf,"CFNumberGetValue");
    *(void **)(&string_value)=dlsym(cf,"CFStringGetCString");
}
static void event_properties(unsigned service,unsigned long long id) {
    const char *keys[]={"Built-In","PrimaryUsagePage","PrimaryUsage","DisplayIntegrated","Transport","Product",0};
    if(!copy_property || !type_id || !boolean_type || !number_type || !string_type || !boolean_value || !number_value || !string_value) {
        printf("INFERNO_HID_PROPERTY registry_id=%llu result=diagnostic_symbols_unavailable\n",id);fflush(0);return;
    }
    for(unsigned i=0;keys[i];i++) {
        Object key=string(0,keys[i],0x08000100);
        Object value=key?copy_property(service,key,0,0):0;
        if(key)release(key);
        if(!value){printf("INFERNO_HID_PROPERTY registry_id=%llu key=%s present=0\n",id,keys[i]);continue;}
        unsigned long type=type_id(value);
        if(type==boolean_type())
            printf("INFERNO_HID_PROPERTY registry_id=%llu key=%s present=1 type=boolean value=%u\n",id,keys[i],(unsigned)boolean_value(value));
        else if(type==number_type()) {
            long long number=0;int ok=number_value(value,4,&number); /* kCFNumberSInt64Type */
            printf("INFERNO_HID_PROPERTY registry_id=%llu key=%s present=1 type=number converted=%d value=%lld\n",id,keys[i],ok,number);
        } else if(type==string_type()) {
            char text[192]={0};int ok=string_value(value,text,sizeof(text),0x08000100);text[191]=0;
            for(unsigned j=0;text[j];j++)if((unsigned char)text[j]<32 || (unsigned char)text[j]>126)text[j]='?';
            printf("INFERNO_HID_PROPERTY registry_id=%llu key=%s present=1 type=string converted=%d value=%.191s\n",id,keys[i],ok,ok?text:"(unavailable)");
        } else printf("INFERNO_HID_PROPERTY registry_id=%llu key=%s present=1 type=other type_id=%lu\n",id,keys[i],type);
        release(value);
    }
    fflush(0);
}
/* HID1.11 short items: Digitizers/TouchScreen Application, one Finger Logical.
 * Report0: tip/in-range/confidence bits,5padding bits,contact ID8,X16,Y16,count8.
 * Coordinates unsigned logical0..32767; no Apple vendor usage or identity. */
static const unsigned char descriptor[]={
    0x05,0x0d,0x09,0x04,0xa1,0x01,
    0x09,0x22,0xa1,0x02,
    0x09,0x42,0x09,0x32,0x09,0x47,0x15,0x00,0x25,0x01,0x75,0x01,0x95,0x03,0x81,0x02,
    0x75,0x05,0x95,0x01,0x81,0x03,
    0x09,0x51,0x15,0x00,0x25,0x7f,0x75,0x08,0x95,0x01,0x81,0x02,
    0x05,0x01,0x09,0x30,0x09,0x31,0x15,0x00,0x26,0xff,0x7f,0x75,0x10,0x95,0x02,0x81,0x02,
    0xc0,0x05,0x0d,0x09,0x54,0x15,0x00,0x25,0x01,0x75,0x08,0x95,0x01,0x81,0x02,0xc0
};
#define LOAD(handle,variable,name) do { *(void **)(&variable)=dlsym(handle,name);if(!variable){printf("INFERNO_HID_SYMBOL_FAILED name=%s\n",name);fflush(0);return -101;} }while(0)
static int initialize(void) {
    void *cf=dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",2);
    void *io=dlopen("/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit",2);
    if(!cf || !io)return -100;
    LOAD(cf,dictionary,"CFDictionaryCreateMutable");LOAD(cf,set,"CFDictionarySetValue");LOAD(cf,release,"CFRelease");
    LOAD(cf,string,"CFStringCreateWithCString");LOAD(cf,data,"CFDataCreate");
    LOAD(io,create,"IOHIDUserDeviceCreate");LOAD(io,report,"IOHIDUserDeviceHandleReportWithTimeStamp");LOAD(io,copy_service,"IOHIDUserDeviceCopyService");
    LOAD(io,object_class,"IOObjectGetClass");LOAD(io,children,"IORegistryEntryGetChildIterator");
    LOAD(io,registry_id,"IORegistryEntryGetRegistryEntryID");LOAD(io,object_release,"IOObjectRelease");
    LOAD(io,iterator_create,"IORegistryEntryCreateIterator");LOAD(io,iterator_next,"IOIteratorNext");LOAD(io,conforms,"IOObjectConformsTo");
    LOAD(io,service_matching,"IOServiceMatching");LOAD(io,matching_service,"IOServiceGetMatchingService");
    LOAD(io,service_open,"IOServiceOpen");LOAD(io,service_close,"IOServiceClose");
    /* Original iOS IOKit lacks the legacy parser export; never invent its ABI. */
    descriptor_parser_exported=dlsym(io,"HIDOpenReportDescriptor")!=0;
    key_callbacks=dlsym(cf,"kCFTypeDictionaryKeyCallBacks");value_callbacks=dlsym(cf,"kCFTypeDictionaryValueCallBacks");
    Object *truth=(Object *)dlsym(cf,"kCFBooleanTrue");
    if(!key_callbacks || !value_callbacks || !truth)return -101;
    true_value=*truth;diagnostic_symbols(cf,io);return 0;
}
static int property(Object dict,const char *key,Object value) {
    Object k=string(0,key,0x08000100);
    if(!k || !value){if(k)release(k);return -1;}
    set(dict,k,value);release(k);return 0;
}
static int text_property(Object dict,const char *key,const char *value) {
    Object v=string(0,value,0x08000100);int result=property(dict,key,v);if(v)release(v);return result;
}
static void node_inventory(unsigned service,const char *relation) {
    unsigned long long id=0;char cls[128]={0};
    int id_status=registry_id(service,&id),class_status=object_class(service,cls);cls[127]=0;
    printf("INFERNO_HID_DEVICE_NODE relation=%s registry_id=%llu id_status=0x%x class=%s class_status=0x%x\n",relation,id,(unsigned)id_status,cls,(unsigned)class_status);fflush(0);
}
static void creation_diagnostics(void) {
    printf("INFERNO_HID_DESCRIPTOR_CHECK bytes=%lu parser_exported=%d parser_invoked=0 result=unavailable\n",(unsigned long)sizeof(descriptor),descriptor_parser_exported);fflush(0);
    Object match=service_matching("IOHIDResource");
    if(!match){printf("INFERNO_HID_RESOURCE_MATCH dictionary=0 service=0\n");fflush(0);return;}
    /* GetMatchingService consumes the dictionary. Type zero/current task are
     * the exact original IOHIDUserDeviceCreate open path. No method is called. */
    unsigned resource=matching_service(0,match),connection=0;
    printf("INFERNO_HID_RESOURCE_MATCH dictionary=1 service=%u\n",resource);fflush(0);
    if(!resource)return;
    node_inventory(resource,"resource_before_create");
    int status=service_open(resource,mach_task_self_,0,&connection);
    printf("INFERNO_HID_RESOURCE_OPEN type=0 status=0x%x connection=%u\n",(unsigned)status,connection);fflush(0);
    if(!status && connection) {
        int close_status=service_close(connection);
        printf("INFERNO_HID_RESOURCE_CLOSE status=0x%x\n",(unsigned)close_status);fflush(0);
    }
    object_release(resource);
}
static void device_inventory(void) {
    unsigned service=copy_service(device);if(!service)return;
    node_inventory(service,"owned_device");
    unsigned iter=0;int status=children(service,"IOService",&iter);
    printf("INFERNO_HID_DEVICE_CHILDREN status=0x%x\n",(unsigned)status);fflush(0);
    if(!status) {
        unsigned child,count=0;
        while((child=iterator_next(iter))) {
            node_inventory(child,"immediate_child");object_release(child);if(++count>=16)break;
        }
        object_release(iter);
    }
    object_release(service);
}
static int create_device(void) {
    int status=initialize();if(status)return status;
    creation_diagnostics();
    Object properties=dictionary(0,0,key_callbacks,value_callbacks);
    Object desc=data(0,descriptor,sizeof(descriptor));
    if(!properties || !desc){if(properties)release(properties);if(desc)release(desc);return -102;}
    int error=property(properties,"ReportDescriptor",desc);
    error|=text_property(properties,"Product","Inferno Operator Touchscreen");
    error|=text_property(properties,"Manufacturer","Inferno companion (owned virtual device)");
    error|=text_property(properties,"Transport","Virtual");
    /* Normal metadata: this honestly named virtual touchscreen belongs to the VM display. */
    error|=property(properties,"Built-In",true_value);
    release(desc);
    if(!error)device=create(0,properties);
    release(properties);
    printf("INFERNO_HID_DEVICE_CREATE success=%d descriptor_bytes=%lu apple_identity=0\n",device!=0,(unsigned long)sizeof(descriptor));fflush(0);
    if(device) {
        unsigned service=copy_service(device);unsigned long long id=0;int status=service?registry_id(service,&id):-1;
        printf("INFERNO_HID_DEVICE_REGISTRY service=%u registry_id=%llu status=0x%x\n",service,id,(unsigned)status);fflush(0);
        if(service)object_release(service);
    }
    if(device)device_inventory();
    return device?0:-103;
}
static int event_service_ready(void) {
    unsigned service=copy_service(device);if(!service)return 0;
    unsigned long long id=0;registry_id(service,&id);
    unsigned iter=0;int found=0;
    if(!iterator_create(service,"IOService",1,&iter)) {
        unsigned node,count=0;
        while((node=iterator_next(iter))) {
            if(conforms(node,"IOHIDEventService")) {
                unsigned long long child_id=0;registry_id(node,&child_id);
                node_inventory(node,"matched_event_service");
                event_properties(node,child_id);
                printf("INFERNO_HID_MATCH device_id=%llu event_service_id=%llu\n",id,child_id);fflush(0);found=1;
            }
            object_release(node);if(found || ++count>=64)break;
        }
        object_release(iter);
    }
    object_release(service);return found;
}
static int send_report(const struct inferno_gesture *g,unsigned x,unsigned y,int touching,const char *phase) {
    unsigned char bytes[7]={(unsigned char)(touching?7:0),1,(unsigned char)x,(unsigned char)(x>>8),(unsigned char)y,(unsigned char)(y>>8),(unsigned char)(touching?1:0)};
    unsigned long long stamp=mach_absolute_time();int result=report(device,stamp,bytes,sizeof(bytes));
    printf("INFERNO_HID_REPORT request_id=%s phase=%s x=%u y=%u touching=%d timestamp=%llu result=0x%x\n",g->request_id,phase,x,y,touching,stamp,(unsigned)result);fflush(0);return result;
}
int inferno_hid_prepare(void) {return device?0:create_device();}
int inferno_hid_dispatch(const struct inferno_gesture *g) {
    if(!device){int status=create_device();if(status)return status;}
    int ready=0;
    for(unsigned tries=0;tries<50 && !inferno_hid_stopping();tries++) {
        if(event_service_ready()){ready=1;break;}usleep(100000);
    }
    device_inventory();
    if(!ready || inferno_hid_stopping())return -104; /* No queued/replayed gesture. */
    unsigned x=g->x0,y=g->y0;
    int result=send_report(g,x,y,1,"down");
    unsigned steps=g->swipe?g->duration_ms/16:1;if(!steps)steps=1;if(steps>120)steps=120;
    for(unsigned i=1;i<=steps && !result && !inferno_hid_stopping();i++) {
        usleep(g->duration_ms*1000/steps);
        if(g->swipe && !inferno_hid_stopping()) {
            x=(unsigned)((int)g->x0+((int)g->x1-(int)g->x0)*(int)i/(int)steps);
            y=(unsigned)((int)g->y0+((int)g->y1-(int)g->y0)*(int)i/(int)steps);
            result=send_report(g,x,y,1,"move");
        }
    }
    int up=send_report(g,x,y,0,inferno_hid_stopping()?"cancel_release":"up");
    return result?result:up;
}
void inferno_hid_close(void) {if(device){release(device);device=0;}}
