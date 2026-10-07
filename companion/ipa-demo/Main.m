// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned demo: original UIKit UI and Foundation bundle resource loading.
#import "../app-probe/UIKitNarrow.h"
extern Class NSClassFromString(NSString *name);
@interface NSObject (DemoBundle)
+ (id)mainBundle;
- (NSString *)pathForResource:(NSString *)name ofType:(NSString *)extension;
@end
@interface NSString (DemoFile)
+ (instancetype)stringWithContentsOfFile:(NSString *)path encoding:(NSUInteger)encoding error:(NSError **)error;
@end
@interface DemoController : UIViewController { UILabel *_count; NSUInteger _value; }
@end
@implementation DemoController
- (void)viewDidLoad {
    [super viewDidLoad];
    UIView *view = [self view];
    [view setBackgroundColor:[UIColor colorWithRed:0.96 green:0.97 blue:0.99 alpha:1]];
    UILabel *title = [[UILabel alloc] initWithFrame:Rect(20,100,374,60)];
    [title setText:@"Imported IPA Demo"]; [title setFont:[UIFont boldSystemFontOfSize:28]];
    [title setTextAlignment:1]; [view addSubview:title];
    NSString *path = [[NSClassFromString(@"NSBundle") mainBundle] pathForResource:@"Message" ofType:@"txt"];
    NSError *error = nil;
    NSString *message = path ? [NSString stringWithContentsOfFile:path encoding:4 error:&error] : nil;
    UILabel *resource = [[UILabel alloc] initWithFrame:Rect(24,190,366,120)];
    [resource setText:message ? message : [NSString stringWithFormat:@"RESOURCE READ FAILED (%ld)", [error code]]];
    [resource setFont:[UIFont systemFontOfSize:21]]; [resource setNumberOfLines:4];
    [resource setTextAlignment:1]; [resource setAccessibilityIdentifier:@"imported-resource"];
    [view addSubview:resource];
    _count = [[UILabel alloc] initWithFrame:Rect(24,350,366,70)];
    [_count setFont:[UIFont boldSystemFontOfSize:32]]; [_count setTextAlignment:1];
    [_count setText:@"Count: 0"]; [_count setAccessibilityIdentifier:@"imported-count"];
    [view addSubview:_count];
    UIButton *button = [UIButton buttonWithType:1];
    [button setFrame:Rect(62,460,290,70)]; [button setTitle:@"Increment" forState:0];
    [[button titleLabel] setFont:[UIFont boldSystemFontOfSize:26]];
    [button setAccessibilityIdentifier:@"imported-increment"];
    [button addTarget:self action:@selector(increment:) forControlEvents:1UL<<6];
    [view addSubview:button];
}
- (void)increment:(id)sender { (void)sender; _value++; [_count setText:[NSString stringWithFormat:@"Count: %lu", _value]]; }
@end
@interface DemoDelegate : NSObject <UIApplicationDelegate> { UIWindow *_window; }
@end
@implementation DemoDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    [_window setRootViewController:[[DemoController alloc] init]]; [_window makeKeyAndVisible]; return 1;
}
@end
int main(int argc, char **argv) { return UIApplicationMain(argc, argv, nil, @"DemoDelegate"); }
