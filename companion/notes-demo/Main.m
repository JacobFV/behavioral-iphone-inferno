// SPDX-License-Identifier: AGPL-3.0-or-later
// Owned UIKit fixture: UITableView, UITextField and NSUserDefaults persistence.
#import "NotesNarrow.h"
static NSString *const NotesKey = @"notes";
static NSString *const LaunchKey = @"launches";
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
@interface NotesController : UIViewController <UITableViewDataSource, UITableViewDelegate, UITextFieldDelegate> {
    UITextField *_field; UITableView *_table; UILabel *_status;
    NSString *_stored; id _rows; NSInteger _launches;
}
@end
@implementation NotesController
// Notes are stored as one newline-joined string under a single defaults key.
- (void)reload {
    id defaults = [NSClassFromString(@"NSUserDefaults") standardUserDefaults];
    _stored = [defaults stringForKey:NotesKey];
    if (!_stored) _stored = @"";
    _rows = [_stored length] ? [_stored componentsSeparatedByString:@"\n"] : nil;
    [_table reloadData];
    [_status setText:[NSString stringWithFormat:@"Launches: %ld | Notes: %lu",(long)_launches,(unsigned long)(_rows ? [_rows count] : 0)]];
}
- (void)viewDidLoad {
    [super viewDidLoad];
    UIView *view = [self view]; [view setBackgroundColor:[UIColor colorWithRed:1 green:1 blue:1 alpha:1]];
    label(view,Rect(24,60,366,40),@"Notes Demo",30);
    _status = label(view,Rect(24,105,366,35),@"",18);
    [_status setAccessibilityIdentifier:@"notes-status"];
    _field = [[NSClassFromString(@"UITextField") alloc] initWithFrame:Rect(24,150,366,44)];
    [_field setBorderStyle:3]; [_field setPlaceholder:@"Type a note"]; [_field setFont:[UIFont systemFontOfSize:20]];
    [_field setDelegate:self]; [_field setAccessibilityIdentifier:@"notes-field"];
    [view addSubview:_field];
    UIButton *add = button(view,Rect(24,205,170,55),@"Add note",self,@selector(add:));
    [add setAccessibilityIdentifier:@"notes-add"];
    UIButton *clear = button(view,Rect(220,205,170,55),@"Clear all",self,@selector(clear:));
    [clear setAccessibilityIdentifier:@"notes-clear"];
    _table = [[NSClassFromString(@"UITableView") alloc] initWithFrame:Rect(0,275,414,560) style:0];
    [_table setDataSource:self]; [_table setDelegate:self]; [_table setRowHeight:56];
    [_table setAccessibilityIdentifier:@"notes-table"];
    [view addSubview:_table];
    [self reload];
}
- (void)add:(id)sender {
    (void)sender;
    NSString *text = [_field text];
    if (![text length]) return;
    id defaults = [NSClassFromString(@"NSUserDefaults") standardUserDefaults];
    NSString *next = [_stored length] ? [NSString stringWithFormat:@"%@\n%@",_stored,text] : text;
    [defaults setObject:next forKey:NotesKey]; [defaults synchronize];
    [_field setText:@""]; [_field resignFirstResponder];
    [self reload];
}
- (void)clear:(id)sender {
    (void)sender;
    id defaults = [NSClassFromString(@"NSUserDefaults") standardUserDefaults];
    [defaults setObject:@"" forKey:NotesKey]; [defaults synchronize];
    [self reload];
}
- (BOOL)textFieldShouldReturn:(id)field { (void)field; [self add:nil]; return 1; }
- (NSInteger)numberOfSectionsInTableView:(id)table { (void)table; return 1; }
- (NSInteger)tableView:(id)table numberOfRowsInSection:(NSInteger)section {
    (void)table; (void)section; return _rows ? (NSInteger)[_rows count] : 0;
}
- (id)tableView:(id)table cellForRowAtIndexPath:(id)path {
    (void)table;
    id cell = [[NSClassFromString(@"UITableViewCell") alloc] initWithStyle:0 reuseIdentifier:nil];
    NSUInteger row = (NSUInteger)[path row];
    [[cell textLabel] setText:row < [_rows count] ? [_rows objectAtIndex:row] : @"?"];
    return cell;
}
- (void)setLaunches:(NSInteger)count { _launches = count; }
@end
@interface NotesDelegate : NSObject <UIApplicationDelegate> { UIWindow *_window; }
@end
@implementation NotesDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)app; (void)options;
    _window = [[UIWindow alloc] initWithFrame:[[UIScreen mainScreen] bounds]];
    UIViewController *root;
    id defaults = [NSClassFromString(@"NSUserDefaults") standardUserDefaults];
    if (!NSClassFromString(@"UITableView") || !NSClassFromString(@"UITextField") || !defaults) {
        root = [[UIViewController alloc] init];
        label([root view],Rect(24,150,366,120),@"Required UIKit/Foundation class unavailable",24);
    } else {
        NSInteger launches = [defaults integerForKey:LaunchKey] + 1;
        [defaults setInteger:launches forKey:LaunchKey]; [defaults synchronize];
        NotesController *notes = [[NotesController alloc] init];
        [notes setLaunches:launches]; root = notes;
    }
    [_window setRootViewController:root];
    [_window makeKeyAndVisible]; return 1;
}
@end
int main(int argc, char **argv) { return UIApplicationMain(argc,argv,nil,@"NotesDelegate"); }
