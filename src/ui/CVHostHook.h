//
//  CVHostHook.h —— 宿主到期标签「直改」方案
//
//  用户要求：
//      「如果可以直接hook掉原宿主的到期时间显示真实的不行就覆盖掉显示真实的」
//
//  所以这里是「优先方案」：找到宿主原本那个显示到期时间的 UILabel，
//  直接把它的 text 改掉 —— 这样连视觉风格都是宿主自己的，最自然。
//
//  只有找不到时才退回 CVOverlay 的「平面覆盖」方案。
//
//  ★ 关键：怎么在不硬编码类名的前提下找到那个标签？
//    测试版 dylib 的做法是遍历 UIButton 的 currentTitle 查白名单，
//    我们沿用同一套「按可见文本 + 位置 + 正则」的思路：
//      1. 遍历 keyWindow 下所有 UILabel
//      2. 排除我们自己的视图
//      3. 文本能匹配日期正则（19xx/20xx-xx-xx）或含「授权至」
//      4. 位置落在到期条区域内（CVLayout 里的坐标）
//    命中即改写。找不到就返回 NO，交给覆盖层。
//
//  ★ 为什么不用 method swizzling 整个 UILabel 的 setText:？
//    那会污染全 App 所有标签，风险远大于收益。
//    这里只在「当前这一帧能看到的标签」里精确挑一个，改完就完事。
//

#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

@interface CVHostHook : NSObject

/// 尝试直接改写宿主到期标签
/// @param expiry 真实到期时间（形如 "2025-06-30 12:00:00"）
/// @return YES = 已成功改写宿主标签（不需要再叠覆盖层显示到期）
///         NO  = 没找到，请退回覆盖层方案
+ (BOOL)applyExpiryText:(nullable NSString *)expiry;

/// 让宿主标签持续跟我们同步（宿主可能定时刷新自己的文案）
/// 传入 nil 取消订阅
+ (void)startKeepAliveWithExpiry:(nullable NSString *)expiry;

/// 停止订阅
+ (void)stopKeepAlive;

/// 诊断：把当前扫到的候选标签打日志（用于排错）
+ (void)logCandidates;

@end

NS_ASSUME_NONNULL_END
