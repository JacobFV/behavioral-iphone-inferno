// SPDX-License-Identifier: AGPL-3.0-or-later
// Sample-local Objective-C ABI declarations, not an SDK or implementation.
#import "../app-probe/UIKitNarrow.h"
extern Class NSClassFromString(NSString *name);
@interface UIView (NavigationDemoTag)
- (void)setTag:(NSInteger)tag;
- (NSInteger)tag;
@end
@class UINavigationController;
@interface UIViewController (NavigationDemoLifecycle)
- (void)setTitle:(NSString *)title;
- (UINavigationController *)navigationController;
- (void)viewWillAppear:(BOOL)animated;
@end
@interface UINavigationController : UIViewController
- (instancetype)initWithRootViewController:(UIViewController *)root;
- (void)pushViewController:(UIViewController *)controller animated:(BOOL)animated;
- (UIViewController *)popViewControllerAnimated:(BOOL)animated;
@end
@interface UIScrollView : UIView
- (void)setContentSize:(CGSize)size;
- (void)setAlwaysBounceVertical:(BOOL)value;
@end
@interface UISwitch : UIView
- (void)setOn:(BOOL)value animated:(BOOL)animated;
- (BOOL)isOn;
- (void)addTarget:(id)target action:(SEL)action forControlEvents:(NSUInteger)events;
@end
@interface NSObject (NavigationDemoBundle)
+ (id)mainBundle;
- (NSString *)pathForResource:(NSString *)name ofType:(NSString *)extension;
@end
@interface NSString (NavigationDemoFile)
+ (instancetype)stringWithContentsOfFile:(NSString *)path encoding:(NSUInteger)encoding error:(NSError **)error;
@end
