// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned probe: shows the guest's network interfaces (getifaddrs) every 3 s, and whether a TCP
// connection to the USB companion's NCM address (192.168.77.1:53) and to 1.1.1.1:443 succeeds.
#import "../app-probe/UIKitNarrow.h"
struct sockaddr { unsigned char sa_len, sa_family; char sa_data[14]; };
struct sockaddr_in { unsigned char sin_len, sin_family; unsigned short sin_port; unsigned int sin_addr; char zero[8]; };
struct ifaddrs { struct ifaddrs *ifa_next; char *ifa_name; unsigned int ifa_flags; struct sockaddr *ifa_addr,
    *ifa_netmask, *ifa_dstaddr; void *ifa_data; };
extern int getifaddrs(struct ifaddrs **); extern void freeifaddrs(struct ifaddrs *);
extern const char *inet_ntop(int, const void *, char *, unsigned int);
extern int socket(int, int, int), connect(int, const void *, unsigned int), close(int), fcntl(int, int, ...);
extern int poll(void *, unsigned int, int), getsockopt(int, int, int, void *, unsigned int *);
struct pollfd { int fd; short events, revents; };
@interface NSObject (NetProbe)
+ (id)scheduledTimerWithTimeInterval:(double)t target:(id)target selector:(SEL)s userInfo:(id)u repeats:(BOOL)r;
@end
extern Class NSClassFromString(NSString *name);

static const char *tcp(unsigned int addr_be, unsigned short port) {
    int s = socket(2, 1, 0); if (s < 0) return "socket failed";
    fcntl(s, 4, 4); // F_SETFL O_NONBLOCK
    struct sockaddr_in a = {16, 2, (unsigned short)((port >> 8) | (port << 8)), addr_be, {0}};
    connect(s, &a, 16);
    struct pollfd p = {s, 4, 0}; // POLLOUT
    int r = poll(&p, 1, 2500), err = -1; unsigned int len = 4;
    if (r > 0) getsockopt(s, 0xffff, 0x1007, &err, &len); // SOL_SOCKET, SO_ERROR
    close(s);
    return r <= 0 ? "timeout" : (err == 0 ? "CONNECTED" : (err == 51 ? "no route (51)" : (err == 61 ? "refused (61)" : "error")));
}

@interface NetController : UIViewController { UILabel *_body; unsigned _n; }
@end
@implementation NetController
- (void)viewDidLoad {
    [super viewDidLoad];
    UIView *view = [self view];
    [view setBackgroundColor:[UIColor colorWithRed:0.05 green:0.1 blue:0.09 alpha:1]];
    UILabel *title = [[UILabel alloc] initWithFrame:Rect(20,60,374,44)];
    [title setText:@"Network Probe"]; [title setFont:[UIFont boldSystemFontOfSize:28]];
    [title setTextColor:[UIColor colorWithRed:0.5 green:1 blue:0.7 alpha:1]]; [title setTextAlignment:1]; [view addSubview:title];
    _body = [[UILabel alloc] initWithFrame:Rect(16,110,382,760)];
    [_body setFont:[UIFont systemFontOfSize:15]]; [_body setNumberOfLines:0];
    [_body setTextColor:[UIColor colorWithRed:0.9 green:0.95 blue:0.92 alpha:1]]; [view addSubview:_body];
    [self refresh:nil];
    [NSClassFromString(@"NSTimer") scheduledTimerWithTimeInterval:3 target:self selector:@selector(refresh:) userInfo:nil repeats:1];
}
- (void)refresh:(id)timer {
    (void)timer; char line[256], text[3000]; int off = 0; text[0] = 0;
    struct ifaddrs *list = 0;
    if (getifaddrs(&list) == 0) {
        for (struct ifaddrs *i = list; i && off < 2600; i = i->ifa_next) {
            if (!i->ifa_addr) continue;
            int fam = i->ifa_addr->sa_family; char addr[64] = "-";
            if (fam == 2) inet_ntop(2, &((struct sockaddr_in *)i->ifa_addr)->sin_addr, addr, 64);
            else if (fam == 30) inet_ntop(30, ((char *)i->ifa_addr) + 8, addr, 64);
            else if (fam == 18) snprintf(addr, 64, "link");
            off += snprintf(text + off, 3000 - off, "%-7s %s%s %s\n", i->ifa_name, (i->ifa_flags & 1) ? "UP" : "down",
                            (i->ifa_flags & 0x40) ? ",RUN" : "", addr);
        }
        freeifaddrs(list);
    }
    snprintf(line, 256, "\nrefresh %u\nTCP 192.168.77.1:53  %s\nTCP 1.1.1.1:443  %s\n", ++_n,
             tcp(0x014da8c0, 53), tcp(0x01010101, 443));
    off += snprintf(text + off, 3000 - off, "%s", line);
    [_body setText:[NSString stringWithFormat:@"%s", text]];
    NSLog(@"INFERNO_NET_PROBE %s", text);
}
@end
@interface NetDelegate : NSObject <UIApplicationDelegate> { UIWindow *_window; }
@end
@implementation NetDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    [_window setRootViewController:[[NetController alloc] init]]; [_window makeKeyAndVisible]; return 1;
}
@end
int main(int argc, char **argv) { return UIApplicationMain(argc, argv, nil, @"NetDelegate"); }
