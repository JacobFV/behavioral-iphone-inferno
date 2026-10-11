// SPDX-License-Identifier: AGPL-3.0-or-later
// Sample-local Objective-C ABI declarations, not an SDK or implementation.
// All classes beyond the shared probe stubs are resolved with NSClassFromString,
// so this app links only symbols already declared by app-probe/stubs.
#import "../app-probe/UIKitNarrow.h"
extern Class NSClassFromString(NSString *name);
@protocol UITableViewDataSource
@end
@protocol UITableViewDelegate
@end
@protocol UITextFieldDelegate
@end
@interface NSObject (NotesDemoRuntime)
+ (id)standardUserDefaults;
- (void)setObject:(id)value forKey:(NSString *)key;
- (NSString *)stringForKey:(NSString *)key;
- (NSInteger)integerForKey:(NSString *)key;
- (void)setInteger:(NSInteger)value forKey:(NSString *)key;
- (BOOL)synchronize;
- (NSUInteger)count;
- (id)objectAtIndex:(NSUInteger)index;
- (NSInteger)row;
- (instancetype)initWithFrame:(CGRect)frame style:(NSInteger)style;
- (instancetype)initWithStyle:(NSInteger)style reuseIdentifier:(NSString *)identifier;
- (UILabel *)textLabel;
@end
@interface NSString (NotesDemoText)
- (id)componentsSeparatedByString:(NSString *)separator;
- (NSUInteger)length;
- (NSString *)stringByTrimmingCharactersInSet:(id)set;
@end
@interface UIView (NotesDemoView)
- (BOOL)resignFirstResponder;
@end
@interface UITextField : UIView
- (NSString *)text;
- (void)setText:(NSString *)text;
- (void)setPlaceholder:(NSString *)text;
- (void)setBorderStyle:(NSInteger)style;
- (void)setDelegate:(id)delegate;
- (void)setFont:(UIFont *)font;
@end
@interface UITableView : UIView
- (void)setDataSource:(id)source;
- (void)setDelegate:(id)delegate;
- (void)setRowHeight:(CGFloat)height;
- (void)reloadData;
@end
