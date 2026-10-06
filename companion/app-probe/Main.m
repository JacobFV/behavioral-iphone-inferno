// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned minimal UIKit fixture. All implementation comes from the running guest.
#import "UIKitNarrow.h"

static void marker(const char *event, NSUInteger count) {
    char buffer[160];
    int length = snprintf(buffer, sizeof(buffer),
                          "INFERNO_UIKIT_PROBE_V1 event=%s count=%lu\n", event, count);
    if (length > 0 && (unsigned long)length < sizeof(buffer)) {
        write(2, buffer, (unsigned long)length);
    }
    NSLog(@"INFERNO_UIKIT_PROBE_V1 event=%s count=%lu", event, count);
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
    [_footer setText:@"One tap changes the counter.\nNo network. No account."];
    [_footer setNumberOfLines:2];
    [_footer setFont:[UIFont systemFontOfSize:16]];
    [_footer setTextColor:cyan];
    [_footer setTextAlignment:1];
    [view addSubview:_footer];
    marker("view-loaded", _count);
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGRect bounds = [[self view] bounds];
    CGFloat width = bounds.size.width;
    CGFloat height = bounds.size.height;
    [_heading setFrame:Rect(16, height * 0.19, width - 32, 46)];
    [_subtitle setFrame:Rect(16, height * 0.19 + 50, width - 32, 28)];
    [_counter setFrame:Rect(16, height * 0.40, width - 32, 64)];
    [_button setFrame:Rect(width * 0.10, height * 0.58, width * 0.80, 76)];
    [_footer setFrame:Rect(16, height * 0.78, width - 32, 56)];
}
- (void)viewDidAppear:(BOOL)animated {
    [super viewDidAppear:animated];
    marker("appeared", _count);
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
    (void)application;
    (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    [_window setRootViewController:[[InfernoProbeController alloc] init]];
    [_window makeKeyAndVisible];
    marker("window-visible-requested", 0);
    return 1;
}
- (void)applicationDidBecomeActive:(UIApplication *)application {
    (void)application;
    marker("active", 0);
}
@end

int main(int argc, char **argv) {
    @autoreleasepool {
        marker("main", 0);
        return UIApplicationMain(argc, argv, nil, @"InfernoProbeDelegate");
    }
}
