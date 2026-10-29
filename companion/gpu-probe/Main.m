// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned probe: which graphics stacks exist in the emulated guest, checked at runtime
// (dlopen/dlsym and class lookup only; no SDK headers). Prints results on screen and to NSLog.
#import "../app-probe/UIKitNarrow.h"
extern Class NSClassFromString(NSString *name);
extern void *dlopen(const char *path, int mode);
extern void *dlsym(void *handle, const char *symbol);
@interface NSObject (Probe)
- (id)initWithAPI:(NSUInteger)api;
- (NSString *)name;
@end

static NSString *check(const char *framework, const char *symbol, NSString *className) {
    void *h = dlopen(framework, 1);
    if (!h) return @"framework: NOT LOADED";
    NSString *sym = @"";
    if (symbol) sym = dlsym(h, symbol) ? @", symbol ok" : @", symbol MISSING";
    NSString *cls = @"";
    if (className) cls = NSClassFromString(className) ? @", class ok" : @", class MISSING";
    return [NSString stringWithFormat:@"loaded%@%@", sym, cls];
}

@interface ProbeController : UIViewController
@end
@implementation ProbeController
- (void)viewDidLoad {
    [super viewDidLoad];
    UIView *view = [self view];
    [view setBackgroundColor:[UIColor colorWithRed:0.08 green:0.09 blue:0.12 alpha:1]];
    UILabel *title = [[UILabel alloc] initWithFrame:Rect(20,70,374,50)];
    [title setText:@"Graphics Probe"]; [title setFont:[UIFont boldSystemFontOfSize:30]];
    [title setTextColor:[UIColor colorWithRed:1 green:1 blue:1 alpha:1]]; [title setTextAlignment:1];
    [view addSubview:title];

    // Metal: does a default device exist?
    NSString *metal = check("/System/Library/Frameworks/Metal.framework/Metal", "MTLCreateSystemDefaultDevice", nil);
    void *mh = dlopen("/System/Library/Frameworks/Metal.framework/Metal", 1);
    id (*create)(void) = mh ? (id (*)(void))dlsym(mh, "MTLCreateSystemDefaultDevice") : 0;
    id device = create ? create() : nil;
    metal = [NSString stringWithFormat:@"%@\ndevice: %@", metal, device ? [device name] : @"nil"];
    // OpenGL ES: can a context be created?
    NSString *gles = check("/System/Library/Frameworks/OpenGLES.framework/OpenGLES", "EAGLGetVersion", @"EAGLContext");
    Class eagl = NSClassFromString(@"EAGLContext");
    id ctx3 = eagl ? [[eagl alloc] initWithAPI:3] : nil;
    id ctx2 = (eagl && !ctx3) ? [[eagl alloc] initWithAPI:2] : nil;
    gles = [NSString stringWithFormat:@"%@\nES3 context: %@  ES2 context: %@", gles, ctx3 ? @"yes" : @"no", ctx3 ? @"-" : (ctx2 ? @"yes" : @"no")];
    NSString *sprite = check("/System/Library/Frameworks/SpriteKit.framework/SpriteKit", 0, @"SKView");
    NSString *ca = check("/System/Library/Frameworks/QuartzCore.framework/QuartzCore", 0, @"CAMetalLayer");

    NSString *rows[4][2] = {{@"Metal", metal}, {@"OpenGL ES", gles}, {@"SpriteKit", sprite}, {@"Core Animation", ca}};
    for (int i = 0; i < 4; i++) {
        UILabel *k = [[UILabel alloc] initWithFrame:Rect(24, 140 + i*120, 366, 30)];
        [k setText:rows[i][0]]; [k setFont:[UIFont boldSystemFontOfSize:22]];
        [k setTextColor:[UIColor colorWithRed:0.55 green:0.8 blue:1 alpha:1]]; [view addSubview:k];
        UILabel *v = [[UILabel alloc] initWithFrame:Rect(24, 172 + i*120, 366, 80)];
        [v setText:rows[i][1]]; [v setFont:[UIFont systemFontOfSize:17]]; [v setNumberOfLines:3];
        [v setTextColor:[UIColor colorWithRed:0.9 green:0.9 blue:0.92 alpha:1]]; [view addSubview:v];
        NSLog(@"INFERNO_GPU_PROBE %@: %@", rows[i][0], rows[i][1]);
    }
    // CPU-composited colour grid: proves ordinary UIKit drawing works whatever the GPU answer.
    for (int i = 0; i < 6; i++) for (int j = 0; j < 2; j++) {
        UIView *cell = [[UIView alloc] initWithFrame:Rect(24 + i*61, 640 + j*61, 55, 55)];
        [cell setBackgroundColor:[UIColor colorWithRed:(i/5.0) green:(j ? 0.7 : 0.3) blue:1 - i/5.0 alpha:1]];
        [view addSubview:cell];
    }
}
@end
@interface ProbeDelegate : NSObject <UIApplicationDelegate> { UIWindow *_window; }
@end
@implementation ProbeDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    [_window setRootViewController:[[ProbeController alloc] init]]; [_window makeKeyAndVisible]; return 1;
}
@end
int main(int argc, char **argv) { return UIApplicationMain(argc, argv, nil, @"ProbeDelegate"); }
