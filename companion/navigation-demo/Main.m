// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned UIKit fixture: ordinary navigation, scroll view, switch, and bundle text.
#import "NavigationNarrow.h"
static NSUInteger selectedItem = 1, savedItem = 0, saveCount = 0;
static BOOL savedEnabled = 0;
static UILabel *label(UIView *parent, CGRect frame, NSString *text, CGFloat size) {
    UILabel *value = [[UILabel alloc] initWithFrame:frame];
    [value setText:text]; [value setFont:[UIFont systemFontOfSize:size]];
    [value setNumberOfLines:0]; [parent addSubview:value]; return value;
}
static UIButton *button(UIView *parent, CGRect frame, NSString *text, id target, SEL action) {
    UIButton *value = [UIButton buttonWithType:1]; [value setFrame:frame];
    [value setTitle:text forState:0]; [[value titleLabel] setFont:[UIFont boldSystemFontOfSize:22]];
    [value addTarget:target action:action forControlEvents:1UL<<6];
    [parent addSubview:value]; return value;
}
// Permit catalog buttons to surrender tracking when UIKit recognizes a drag.
// Ordinary touch-up-inside taps and the default delay policy remain unchanged.
@interface CatalogScrollView : UIScrollView
@end
@implementation CatalogScrollView
- (BOOL)touchesShouldCancelInContentView:(UIView *)view {
    if ([view isKindOfClass:[UIButton class]]) return 1;
    return [super touchesShouldCancelInContentView:view];
}
@end
@interface DetailController : UIViewController { UISwitch *_enabled; UILabel *_state; }
@end
@implementation DetailController
- (void)viewDidLoad {
    [super viewDidLoad]; [self setTitle:[NSString stringWithFormat:@"Item %lu", selectedItem]];
    UIView *view = [self view]; [view setBackgroundColor:[UIColor colorWithRed:0.98 green:0.98 blue:1 alpha:1]];
    label(view,Rect(24,110,366,60),[NSString stringWithFormat:@"Detail for item %lu",selectedItem],28);
    NSString *path = [[NSClassFromString(@"NSBundle") mainBundle] pathForResource:@"Guide" ofType:@"txt"];
    NSError *error = nil;
    NSString *message = path ? [NSString stringWithContentsOfFile:path encoding:4 error:&error] : nil;
    UILabel *resource = label(view,Rect(24,190,366,200),message ? message : @"RESOURCE READ FAILED",21);
    [resource setAccessibilityIdentifier:@"navigation-resource"];
    label(view,Rect(24,405,220,55),@"Enable this option",22);
    _enabled = [[NSClassFromString(@"UISwitch") alloc] initWithFrame:Rect(300,415,51,31)];
    [_enabled setOn:savedEnabled animated:0]; [_enabled setAccessibilityIdentifier:@"navigation-switch"];
    [_enabled addTarget:self action:@selector(optionChanged:) forControlEvents:1UL<<12];
    [view addSubview:_enabled];
    _state = label(view,Rect(24,480,366,45),savedEnabled ? @"Option: On" : @"Option: Off",22);
    UIButton *save = button(view,Rect(60,550,294,65),@"Save and return",self,@selector(save:));
    [save setAccessibilityIdentifier:@"navigation-save"];
    label(view,Rect(24,665,366,85),@"Back returns without saving. Saved values remain in this app process.",18);
}
- (void)optionChanged:(id)sender {
    (void)sender; [_state setText:[_enabled isOn] ? @"Option: On" : @"Option: Off"];
}
- (void)save:(id)sender {
    (void)sender; savedEnabled = [_enabled isOn]; savedItem = selectedItem; saveCount++;
    [[self navigationController] popViewControllerAnimated:1];
}
@end
@interface CatalogController : UIViewController { UILabel *_summary; }
@end
@implementation CatalogController
- (void)viewDidLoad {
    [super viewDidLoad]; [self setTitle:@"Navigation Demo"];
    UIView *view = [self view]; [view setBackgroundColor:[UIColor colorWithRed:1 green:1 blue:1 alpha:1]];
    _summary = label(view,Rect(24,100,366,65),@"No saved item. Saves: 0",20);
    [_summary setAccessibilityIdentifier:@"navigation-summary"];
    label(view,Rect(24,172,366,35),@"Scroll to item 12, then open it.",18);
    UIScrollView *scroll = [[CatalogScrollView alloc] initWithFrame:Rect(0,225,414,600)];
    [scroll setContentSize:(CGSize){414,1300}]; [scroll setAlwaysBounceVertical:1];
    [scroll setCanCancelContentTouches:1];
    [scroll setAccessibilityIdentifier:@"navigation-catalog"]; [view addSubview:scroll];
    for (NSUInteger i=1;i<=12;i++) {
        UIButton *row = button(scroll,Rect(30,(i-1)*100+10,354,75),[NSString stringWithFormat:@"Open item %lu",i],self,@selector(openItem:));
        [row setTag:(NSInteger)i]; [row setAccessibilityIdentifier:[NSString stringWithFormat:@"navigation-item-%lu",i]];
    }
    label(scroll,Rect(30,1210,354,60),@"End of catalog — 12 items",19);
}
- (void)viewWillAppear:(BOOL)animated {
    [super viewWillAppear:animated];
    if (saveCount) [_summary setText:[NSString stringWithFormat:@"Saved item: %lu | Option: %@\nSaves: %lu",savedItem,savedEnabled ? @"On" : @"Off",saveCount]];
}
- (void)openItem:(UIButton *)sender {
    NSInteger number = [sender tag]; if (number < 1 || number > 12) return;
    selectedItem = (NSUInteger)number;
    [[self navigationController] pushViewController:[[DetailController alloc] init] animated:1];
}
@end
@interface NavigationDelegate : NSObject <UIApplicationDelegate> { UIWindow *_window; }
@end
@implementation NavigationDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    Class navClass = NSClassFromString(@"UINavigationController");
    if (!navClass || !NSClassFromString(@"UIScrollView") || !NSClassFromString(@"UISwitch")) {
        UIViewController *failure = [[UIViewController alloc] init];
        [[failure view] setBackgroundColor:[UIColor colorWithRed:1 green:1 blue:1 alpha:1]];
        label([failure view],Rect(24,150,366,120),@"Required UIKit class unavailable",24);
        [_window setRootViewController:failure];
    } else {
        UINavigationController *nav = [[navClass alloc] initWithRootViewController:[[CatalogController alloc] init]];
        [_window setRootViewController:nav];
    }
    [_window makeKeyAndVisible]; return 1;
}
@end
int main(int argc, char **argv) { return UIApplicationMain(argc,argv,nil,@"NavigationDelegate"); }
