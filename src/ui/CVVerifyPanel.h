//
//  CVVerifyPanel.h —— 全屏卡密验证界面（自绘，不依赖宿主）
//
//  设计要点：
//    1. 真正的全屏：frame = 整个 window bounds，盖住宿主一切
//    2. 不 import 宿主任何类，只依赖 UIKit
//    3. 验证成功 → 通知宿主，自己 removeFromSuperview（"验证成功就没有了"）
//    4. 验证失败 → 界内提示条，不弹系统 Alert（避免和宿主冲突）
//
//  用法：
//      CVVerifyPanel *p = [[CVVerifyPanel alloc] initWithVerifier:verifier];
//      p.onVerified = ^(T3LoginResult *r, NSString *card, NSString *stateCode) { ... };
//      [p showInWindow];
//

#import <UIKit/UIKit.h>
#import "T3Verify.h"

NS_ASSUME_NONNULL_BEGIN

typedef void(^CVVerifySuccessBlock)(T3LoginResult *result, NSString *card, NSString *stateCode);

@interface CVVerifyPanel : UIView

/// 验证成功回调（在主线程）
@property (nonatomic, copy, nullable) CVVerifySuccessBlock onVerified;

/// 用户主动关闭（预留，一般不给关）
@property (nonatomic, copy, nullable) dispatch_block_t onDismissRequested;

- (instancetype)initWithVerifier:(T3Verify *)verifier;

/// 挂到 keyWindow 上，全屏显示（带淡入动画）
- (void)showInWindow;

/// 全屏退出（验证成功后自动调用）
- (void)dismiss;

@end

NS_ASSUME_NONNULL_END
