// SPDX-License-Identifier: AGPL-3.0-or-later
// Self-authored ABI declarations for this one owned fixture, not an SDK.
typedef signed char BOOL;
typedef long NSInteger;
typedef unsigned long NSUInteger;
typedef double CGFloat;
typedef struct { CGFloat x, y; } CGPoint;
typedef struct { CGFloat width, height; } CGSize;
typedef struct { CGPoint origin; CGSize size; } CGRect;
static inline CGRect Rect(CGFloat x, CGFloat y, CGFloat width, CGFloat height) {
    return (CGRect){{x, y}, {width, height}};
}
#ifndef nil
#define nil ((id)0)
#endif
@class NSString, NSDictionary, UIApplication;
__attribute__((objc_root_class))
@interface NSObject {
    // Original ARM64 NSObject has an eight-byte isa at offset zero. Clang
    // folds ivar offsets in direct NSObject subclasses, so omitting this
    // header makes our delegate's _window overwrite its class pointer.
    Class isa;
}
+ (instancetype)alloc;
- (instancetype)init;
@end
@interface NSString : NSObject
+ (instancetype)stringWithFormat:(NSString *)format, ...;
@end
@interface UIColor : NSObject
+ (instancetype)colorWithRed:(CGFloat)red green:(CGFloat)green blue:(CGFloat)blue alpha:(CGFloat)alpha;
@end
@interface UIFont : NSObject
+ (instancetype)systemFontOfSize:(CGFloat)size;
+ (instancetype)boldSystemFontOfSize:(CGFloat)size;
@end
@interface UIView : NSObject
- (instancetype)initWithFrame:(CGRect)frame;
- (CGRect)bounds;
- (void)setFrame:(CGRect)frame;
- (void)setBackgroundColor:(UIColor *)color;
- (void)addSubview:(UIView *)view;
- (void)setAccessibilityIdentifier:(NSString *)identifier;
@end
@interface UILabel : UIView
- (void)setText:(NSString *)text;
- (void)setTextColor:(UIColor *)color;
- (void)setFont:(UIFont *)font;
- (void)setTextAlignment:(NSInteger)alignment;
- (void)setNumberOfLines:(NSInteger)lines;
@end
@interface UIButton : UIView
+ (instancetype)buttonWithType:(NSInteger)type;
- (void)setTitle:(NSString *)title forState:(NSUInteger)state;
- (void)setTitleColor:(UIColor *)color forState:(NSUInteger)state;
- (UILabel *)titleLabel;
- (void)addTarget:(id)target action:(SEL)action forControlEvents:(NSUInteger)events;
@end
@interface UIViewController : NSObject
- (UIView *)view;
- (void)viewDidLoad;
- (void)viewDidLayoutSubviews;
- (void)viewDidAppear:(BOOL)animated;
@end
@interface UIWindow : UIView
- (void)setRootViewController:(UIViewController *)controller;
- (void)makeKeyAndVisible;
@end
@interface UIScreen : NSObject
+ (instancetype)mainScreen;
- (CGRect)bounds;
@end
@protocol UIApplicationDelegate
@end
extern int UIApplicationMain(int argc, char **argv, NSString *principal, NSString *delegate);
extern void NSLog(NSString *format, ...);
extern int snprintf(char *buffer, unsigned long size, const char *format, ...);
extern long write(int descriptor, const void *buffer, unsigned long length);
