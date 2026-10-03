//
//  CVOverlay.h —— 主页覆盖层（到期时间 + 按钮屏蔽）
//
//  这个层挂在宿主主界面之上，做两件事：
//    ① 覆盖「授权至：2099-12-31 23:59:59」那一行，显示真实到期时间
//    ② 在 6 个按钮上盖透明屏蔽块，让它们点不动
//       同时放行「打开菜单」和顶部「音乐键」
//
//  ★ 设计原则：触摸只在这两类区域内被拦截，其它位置一律穿透，
//     保证宿主其它功能（滑动、其它按钮）完全不受影响。
//
//  用法：
//      CVOverlay *ov = [[CVOverlay alloc] init];
//      ov.expiryText = @"2025-06-30 12:00:00";
//      [ov attachToWindow];        // 挂载
//      [ov dismiss];               // 摘除
//

#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

@interface CVOverlay : UIView

/// 要显示的到期时间（nil / 空 → 显示占位）
@property (nonatomic, copy, nullable) NSString *expiryText;

/// 左侧设备描述，默认 @"iPhone 13 · iOS 18.4.1"
@property (nonatomic, copy, nullable) NSString *deviceText;

/// 挂到 keyWindow（幂等，重复调用只会更新）
- (void)attachToWindow;

/// 从父视图移除
- (void)dismiss;

/// ★ 关键：判断某个点是否落在"要屏蔽的 6 个按钮"里
/// 宿主控制器在收到触摸时可以问一句，双重保险
- (BOOL)shouldBlockTouchAtPoint:(CGPoint)pt;

@end

NS_ASSUME_NONNULL_END
