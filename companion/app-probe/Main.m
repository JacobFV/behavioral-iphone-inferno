// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned minimal UIKit fixture. All implementation comes from the running guest.
#import "UIKitNarrow.h"
#include "EventRecord.h"
#include "LoopbackEvent.h"
#include "OwnedClock.h"
extern int open(const char *,int,...),close(int),ftruncate(int,long long),fchmod(int,unsigned short),getpid(void),getuid(void),*__error(void);
static struct {const char *hook;unsigned long long ticks;} timing[5];
static struct {const char *name;NSUInteger count;} pending_events[16];
static unsigned timing_used,timing_mask,pending_used;
static int timing_queued,timing_flushed,timing_failed;
static const char *timing_stage="pending";
static UILabel *diagnostic_footer;
static void timing_flush(void *unused);
static void timing_timeout(void *unused);
static void capture(const char *hook,unsigned bit,unsigned long long ticks) {
    if(timing_mask&bit)return; // first launch only
    if(timing_used==5 || !ticks) {timing_failed=1;timing_stage="capture-error";return;}
    timing[timing_used].hook=hook;timing[timing_used++].ticks=ticks;timing_mask|=bit;
}
static void maybe_flush(void) {
    if(!timing_failed && !timing_queued && timing_mask==31) {
        timing_queued=1;dispatch_async_f(&_dispatch_main_q,0,timing_flush);
    }
}
static int event_fd=-1;
static unsigned event_sequence,event_bytes;
static int event_identity_valid,network_result=-2,network_errno;
static char event_boot[37],event_path[INFERNO_EVENT_PATH_LIMIT];
static const char *event_stage="not-started";
static int event_errno,event_uid,event_failed;
static void event_error(const char *stage,int error) {
    if(!event_failed) {event_stage=stage;event_errno=error;event_failed=1;}
    NSLog(@"INFERNO_UIKIT_EVENT_FILE_ERROR stage=%s errno=%d",stage,error);
}
static void event_start(void) {
    event_uid=getuid();
    int boot_result=inferno_boot_uuid(event_boot);
    if(event_uid!=501) {event_error("uid",0);return;}
    if(boot_result) {event_error("boot",inferno_boot_query_errno);return;}
    event_identity_valid=1;
    NSString *home=NSHomeDirectory();
    if(!home || [home isEqualToString:@"/var/mobile"] || [home isEqualToString:@"/var/mobile/"] || [home isEqualToString:@"/private/var/mobile"] || [home isEqualToString:@"/private/var/mobile/"]) {event_error("no-container",0);return;}
    NSError *directory_error=nil;
    NSURL *cache=[[NSFileManager defaultManager] URLForDirectory:13 inDomain:1 appropriateForURL:nil create:1 error:&directory_error];
    if(!cache) {event_error("cache-url",directory_error?(int)[directory_error code]:0);return;}
    const char *path=[[[cache path] stringByAppendingPathComponent:@"org.inferno.companion.probe.events"] UTF8String];
    int length=path?snprintf(event_path,sizeof(event_path),"%s",path):-1;
    if(length<=0 || length>=(int)sizeof(event_path) || event_path[0]!='/') {event_error("cache-path",0);return;}
    event_fd=open(event_path,1|0x200|0x100,0600);
    if(event_fd<0) {event_error("open",*__error());return;}
    struct inferno_event_stat st;
    const char *failure=0;int error=0;
    if(fstat(event_fd,&st)) {failure="fstat";error=*__error();}
    else if((st.mode&0170000)!=0100000 || st.uid!=501 || st.nlink!=1)failure="identity";
    else if(fchmod(event_fd,0600)) {failure="chmod";error=*__error();}
    else if(ftruncate(event_fd,0)) {failure="truncate";error=*__error();}
    if(failure) {event_error(failure,error);close(event_fd);event_fd=-1;}
    else event_stage="ready";
}

static void event_store(const char *event,NSUInteger count) {
    if(!event_identity_valid || event_sequence>=64 || !inferno_event_name(event) || count>1000000)return;
    char line[192];
    int n=snprintf(line,sizeof(line),"INFERNO_EVENT_V1 %s %d %u %s %lu\n",event_boot,getpid(),++event_sequence,event,count);
    if(n<=0 || n>=(int)sizeof(line) || event_bytes+(unsigned)n>INFERNO_EVENT_LIMIT)return;
    network_result=inferno_send_event(line,(unsigned)n,&network_errno);
    if(event_fd<0)return;
    unsigned done=0;
    while(done<(unsigned)n) {long k=write(event_fd,line+done,(unsigned)n-done);if(k<0 && *__error()==4)continue;if(k<=0) {event_error("write",k<0?*__error():0);close(event_fd);event_fd=-1;return;}done+=(unsigned)k;}
    event_bytes+=(unsigned)n;
}

static void marker(const char *event, NSUInteger count) {
    if(!timing_flushed) {
        if(pending_used<16) {pending_events[pending_used].name=event;pending_events[pending_used++].count=count;}
        else {timing_failed=1;timing_stage="event-buffer-full";}
        return;
    }
    event_store(event,count);
    char buffer[160];
    int length = snprintf(buffer, sizeof(buffer),
                          "INFERNO_UIKIT_PROBE_V1 event=%s count=%lu\n", event, count);
    if (length > 0 && (unsigned long)length < sizeof(buffer)) {
        write(2, buffer, (unsigned long)length);
    }
    NSLog(@"INFERNO_UIKIT_PROBE_V1 event=%s count=%lu", event, count);
}

static void update_footer(void) {
    [diagnostic_footer setText:[NSString stringWithFormat:@"TIMING %s EVENT uid=%d boot=%d/%lu e=%d\n%s errno=%d NET=%d e=%d\n%s",timing_stage,event_uid,inferno_boot_query_result,inferno_boot_query_length,inferno_boot_query_errno,event_stage,event_errno,network_result,network_errno,event_path]];
}
static void timing_timeout(void *unused) {
    (void)unused;
    if(timing_flushed || timing_failed)return;
    timing_failed=1;timing_stage="bootstrap-timeout";update_footer();
}
static void timing_flush(void *unused) {
    (void)unused;
    if(timing_failed || timing_mask!=31)return;
    struct inferno_timebase base={0,0};
    if(mach_timebase_info(&base) || !base.numer || !base.denom) {
        timing_failed=1;timing_stage="timebase-error";update_footer();return;
    }
    event_start(); // all first-launch boundaries already captured and returned
    if(!event_identity_valid) {timing_failed=1;timing_stage="identity-error";update_footer();return;}
    timing_stage="sending";
    for(unsigned i=0;i<timing_used;i++) {
        char line[192];
        int n=snprintf(line,sizeof(line),"INFERNO_TIMING_V1 %s %d %u %s %llu %u %u\n",event_boot,getpid(),i+1,timing[i].hook,timing[i].ticks,base.numer,base.denom);
        if(n<=0 || n>=(int)sizeof(line)) {timing_failed=1;timing_stage="format-error";break;}
        network_result=inferno_send_event(line,(unsigned)n,&network_errno);
        if(network_result) {timing_failed=1;timing_stage="send-error";break;}
    }
    if(!timing_failed)timing_stage="sent-not-acknowledged";
    timing_flushed=1;
    for(unsigned i=0;i<pending_used;i++)marker(pending_events[i].name,pending_events[i].count);
    pending_used=0;update_footer();
}

@interface InfernoProbeController : UIViewController {
    UILabel *_heading;
    UILabel *_subtitle;
    UILabel *_counter;
    UILabel *_footer;
    UIButton *_button;
    NSUInteger _count;
}
- (void)increment:(id)sender;
@end

@implementation InfernoProbeController
- (void)viewDidLoad {
    [super viewDidLoad];
    UIView *view = [self view];
    UIColor *white = [UIColor colorWithRed:1 green:1 blue:1 alpha:1];
    UIColor *cyan = [UIColor colorWithRed:0.3 green:0.88 blue:0.96 alpha:1];
    [view setBackgroundColor:[UIColor colorWithRed:0.04 green:0.08 blue:0.18 alpha:1]];
    _heading = [[UILabel alloc] initWithFrame:Rect(0, 0, 0, 0)];
    [_heading setText:@"INFERNO PROBE"];
    [_heading setFont:[UIFont boldSystemFontOfSize:30]];
    [_heading setTextColor:white];
    [_heading setTextAlignment:1];
    [view addSubview:_heading];
    _subtitle = [[UILabel alloc] initWithFrame:Rect(0, 0, 0, 0)];
    [_subtitle setText:@"Owned app · guest UIKit"];
    [_subtitle setFont:[UIFont systemFontOfSize:17]];
    [_subtitle setTextColor:cyan];
    [_subtitle setTextAlignment:1];
    [view addSubview:_subtitle];
    _counter = [[UILabel alloc] initWithFrame:Rect(0, 0, 0, 0)];
    [_counter setText:@"Tap count: 0"];
    [_counter setFont:[UIFont boldSystemFontOfSize:38]];
    [_counter setTextColor:white];
    [_counter setTextAlignment:1];
    [_counter setAccessibilityIdentifier:@"inferno.counter"];
    [view addSubview:_counter];
    _button = [UIButton buttonWithType:1]; // UIButtonTypeSystem
    [_button setTitle:@"INCREMENT" forState:0]; // UIControlStateNormal
    [_button setTitleColor:[UIColor colorWithRed:0.04 green:0.08 blue:0.18 alpha:1] forState:0];
    [[_button titleLabel] setFont:[UIFont boldSystemFontOfSize:23]];
    [_button setBackgroundColor:[UIColor colorWithRed:1 green:0.64 blue:0.12 alpha:1]];
    [_button setAccessibilityIdentifier:@"inferno.increment"];
    [_button addTarget:self action:@selector(increment:) forControlEvents:(1UL << 6)];
    [view addSubview:_button]; // UIControlEventTouchUpInside
    _footer = [[UILabel alloc] initWithFrame:Rect(0, 0, 0, 0)];
    diagnostic_footer=_footer;
    update_footer();
    [_footer setNumberOfLines:0];
    [_footer setLineBreakMode:1];
    [_footer setFont:[UIFont systemFontOfSize:12]];
    [_footer setTextColor:cyan];
    [_footer setTextAlignment:1];
    [view addSubview:_footer];
    marker("view-loaded", _count);
    update_footer();
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    update_footer();
    CGRect bounds = [[self view] bounds];
    CGFloat width = bounds.size.width;
    CGFloat height = bounds.size.height;
    [_heading setFrame:Rect(16, height * 0.19, width - 32, 46)];
    [_subtitle setFrame:Rect(16, height * 0.19 + 50, width - 32, 28)];
    [_counter setFrame:Rect(16, height * 0.40, width - 32, 64)];
    [_button setFrame:Rect(width * 0.10, height * 0.58, width * 0.80, 76)];
    [_footer setFrame:Rect(16, height * 0.75, width - 32, height * 0.21)];
}
- (void)viewDidAppear:(BOOL)animated {
    capture("appeared",8,mach_absolute_time());
    [super viewDidAppear:animated];
    marker("appeared", _count);
    maybe_flush();
}
- (void)increment:(id)sender {
    (void)sender;
    ++_count;
    [_counter setText:[NSString stringWithFormat:@"Tap count: %lu", _count]];
    marker("tap", _count);
}
@end

@interface InfernoProbeDelegate : NSObject <UIApplicationDelegate> {
    UIWindow *_window;
}
@end
@implementation InfernoProbeDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    capture("launch-delegate",2,mach_absolute_time());
    (void)application;
    (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    [_window setRootViewController:[[InfernoProbeController alloc] init]];
    [_window makeKeyAndVisible];
    capture("window-request",4,mach_absolute_time());
    marker("window-visible-requested", 0);
    dispatch_after_f(dispatch_time(0,120000000000LL),&_dispatch_main_q,0,timing_timeout);
    maybe_flush();
    return 1;
}
- (void)applicationDidBecomeActive:(UIApplication *)application {
    capture("active",16,mach_absolute_time());
    (void)application;
    marker("active", 0);
    maybe_flush();
}
@end

int main(int argc, char **argv) {
    capture("main",1,mach_absolute_time());
    @autoreleasepool {
        marker("main", 0);
        return UIApplicationMain(argc, argv, nil, @"InfernoProbeDelegate");
    }
}
