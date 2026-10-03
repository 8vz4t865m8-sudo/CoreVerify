//
//  CoreVerify.m —— 主入口（dylib 的 constructor）
//
//  ═══════════════════════════════════════════════════════════════════════════
//   CoreVerify · 全屏卡密验证 + 主页覆盖
//
//   ★ 这个 dylib 与 v3（CoreOffline）是两个完全独立的方向：
//       v3      —— 试图接管宿主卡密系统（5 个 dlsym 注入点），已放弃
//       CoreVerify —— 退而求其次：只做界面，不碰宿主内部
//
//   ═══════════════════════════════════════════════════════════════════════════
//   本版做什么（用户明确的三件事）
//   ═══════════════════════════════════════════════════════════════════════════
//
//   ① 全屏卡密验证界面
//        · 自绘，不依赖宿主任何类
//        · 验证逻辑用 T3 SDK（真实网络验证，调用码/公钥来自 T3Example）
//        · 验证成功 → 界面移除（"验证成功就没有了"）
//
//   ② 覆盖到期时间
//        · 先尝试 hook 宿主原来的到期标签（若找得到）
//        · 找不到就平面覆盖：在「授权至：」位置画一条同款胶囊，显示真实到期
//
//   ③ 屏蔽 6 个按钮
//        · 查看公告 / 启动游戏 / 提交工单 / 检查更新 / 工单进度 / 激活续时
//        · 点了没反应
//        · ★ 放行「打开菜单」和顶部「音乐键」
//
//   ═══════════════════════════════════════════════════════════════════════════
//   为什么这次不用 v3 那 5 个注入点
//   ═══════════════════════════════════════════════════════════════════════════
//     那 5 个点（CoreOfflineBootstrap / Prepare / Finalize / RemoteOpen /
//     RemoteFault）是宿主"功能留白"，补上它们属于接管宿主生命周期，
//     风险高且属于用户已放弃的方向。
//     本版走"旁观者"路线：只在 window 上叠一层，宿主内部完全不动。
//
//   ═══════════════════════════════════════════════════════════════════════════

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <objc/runtime.h>

#import "CVLog.h"
#import "CVLayout.h"
#import "ui/CVVerifyPanel.h"
#import "ui/CVOverlay.h"
#import "ui/CVHostHook.h"
#import "t3sdk/T3Verify.h"

// ══════════════════════════════════════════════════════════════════════════
//  T3 配置 —— 直接取自 T3Example_iOS_Dialog/main.m（与宿主一致的那套）
// ══════════════════════════════════════════════════════════════════════════

static NSString * const kT3LoginCode     = @"0AAD3A3337741A5B";
static NSString * const kT3NoticeCode    = @"7EB0F4A8272A7EBD";
static NSString * const kT3VersionCode   = @"61D5FC87F536273F";
static NSString * const kT3HeartbeatCode = @"A44066FE62E69F9D";
// ★ 逐字节从测试版 dylib 的 __cstring（偏移 0x23f8b）与 T3 官方示例 main.m 双重核对
static NSString * const kT3AppKey        = @"1e45cd9daa2d5d7dfc6d8e66abe43b0a";
static NSString * const kT3LocalVersion  = @"1000";

static NSString * const kT3RsaPublicKey =
    @"-----BEGIN PUBLIC KEY-----\n"
     "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDYYJ1hSbVwyCrgpkYi/XuCd9Jm\n"
     "FFji4HfuEG9g17rXkYRmj72xNIKZYZgIMH/8gpiS5AI660o0mMdhYnuQsYEP+5ZD\n"
     "+wVoyiM7EQ9Qnc0hxy7U4dytDKLTJR0RTtpv3LcCIal+jB7yqXY0u0QzOycRY09C\n"
     "4ewpg/EmXG9CslntyQIDAQAB\n"
     "-----END PUBLIC KEY-----";

// 心跳
static const NSTimeInterval kCVHeartbeatInterval = 60.0;
static const int kCVMaxHeartbeatFail = 5;

// NSUserDefaults key（与 CVVerifyPanel 保持一致）
static NSString * const kCVPrefSavedCard = @"cv_saved_card";
static NSString * const kCVPrefStateCode = @"cv_state_code";
static NSString * const kCVPrefEndTime   = @"cv_end_time";

// ══════════════════════════════════════════════════════════════════════════
//  CoreVerify 主控
// ══════════════════════════════════════════════════════════════════════════

@interface CoreVerify : NSObject
@property (nonatomic, strong) T3Verify *verifier;
@property (nonatomic, strong) CVVerifyPanel *panel;
@property (nonatomic, strong) CVOverlay *overlay;
@property (nonatomic, strong) NSTimer *heartbeatTimer;
@property (nonatomic, assign) int heartbeatFail;
@property (nonatomic, copy) NSString *card;
@property (nonatomic, copy) NSString *stateCode;
@property (nonatomic, copy) NSString *endTime;
@property (nonatomic, assign) BOOL installed;
@property (nonatomic, assign) BOOL didShowPanel;
@end

@implementation CoreVerify

+ (instancetype)shared {
    static CoreVerify *s;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ s = [[CoreVerify alloc] init]; });
    return s;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        _heartbeatFail = 0;
    }
    return self;
}

#pragma mark - 启动装配

- (void)start {
    if (self.installed) return;
    self.installed = YES;

    CVLog(@"════════════════════════════════════════════");
    CVLog(@" CoreVerify 启动 (v1)");
    CVLog(@" 日志文件: %@", CVLogFilePath());
    CVLog(@"════════════════════════════════════════════");

    [self setupT3];
    [self watchLifecycle];
}

- (void)setupT3 {
    self.verifier = [[T3Verify alloc] init];
    NSError *err = nil;
    BOOL ok = NO;
    @try {
        ok = [self.verifier initRsaWithLoginCode:kT3LoginCode
                                      noticeCode:kT3NoticeCode
                                     versionCode:kT3VersionCode
                                   heartbeatCode:kT3HeartbeatCode
                                          appkey:kT3AppKey
                                    rsaPublicKey:kT3RsaPublicKey
                                           error:&err];
    } @catch (NSException *e) {
        CVLog(@"[T3] ❌ 初始化抛异常: %@", e.reason);
    }

    if (ok && !err) {
        CVLog(@"[T3] ✅ SDK 装配成功（RSA 模式）");
    } else {
        CVLog(@"[T3] ⚠️ SDK 装配失败: %@", err ? err.localizedDescription : @"未知原因");
        CVLog(@"[T3] 验证界面仍会显示，但点验证会失败");
    }
}

/// 监听窗口出现（宿主可能晚于 dylib 初始化才建 window）
- (void)watchLifecycle {
    [[NSNotificationCenter defaultCenter] addObserver:self
                                             selector:@selector(onDidBecomeActive)
                                                 name:UIApplicationDidBecomeActiveNotification
                                               object:nil];

    // 先试一次（dylib 可能注入在 app 启动之后）
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.0 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{ [self onDidBecomeActive]; });
}

- (void)onDidBecomeActive {
    if (self.didShowPanel) return;

    UIWindow *win = [self keyWindow];
    if (!win || !win.rootViewController) {
        // 宿主还没准备好，继续等
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{ [self onDidBecomeActive]; });
        return;
    }

    self.didShowPanel = YES;
    CVLog(@"[主控] 宿主窗口就绪 root=%@",
          NSStringFromClass([win.rootViewController class]));

    [self showVerifyFlow];
}

#pragma mark - ① 验证流程

- (void)showVerifyFlow {
    NSString *savedCard = [[NSUserDefaults standardUserDefaults] stringForKey:kCVPrefSavedCard];

    if (savedCard.length > 0) {
        CVLog(@"[主控] 发现已保存卡密，尝试自动登录 …");
        [self autoLoginWithCard:savedCard];
    } else {
        CVLog(@"[主控] 无已保存卡密，显示全屏验证界面");
        [self presentPanel];
    }
}

- (void)presentPanel {
    if (self.panel.superview) return;

    self.panel = [[CVVerifyPanel alloc] initWithVerifier:self.verifier];

    __weak typeof(self) weakSelf = self;
    self.panel.onVerified = ^(T3LoginResult *result, NSString *card, NSString *stateCode) {
        [weakSelf onVerifySuccessWithResult:result card:card stateCode:stateCode];
    };
    [self.panel showInWindow];
}

- (void)autoLoginWithCard:(NSString *)card {
    __weak typeof(self) weakSelf = self;
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        NSString *mc = [T3Verify getMachineCode];
        T3LoginResult *r = nil;
        @try {
            r = [weakSelf.verifier loginWithKami:card imei:mc];
        } @catch (NSException *e) {
            r = [T3LoginResult fail:@"自动登录异常"];
        }
        dispatch_async(dispatch_get_main_queue(), ^{
            typeof(self) self = weakSelf;
            if (!self) return;
            if (r && r.success) {
                CVLog(@"[主控] ✅ 自动登录成功，到期 %@", r.endTime ?: @"(空)");
                [self onVerifySuccessWithResult:r card:card stateCode:r.statecode ?: @""];
            } else {
                CVLog(@"[主控] ❌ 自动登录失败（%@），转手动输入", r.error ?: @"未知");
                [[NSUserDefaults standardUserDefaults] removeObjectForKey:kCVPrefSavedCard];
                [[NSUserDefaults standardUserDefaults] synchronize];
                self.didShowPanel = NO;
                [self presentPanel];
            }
        });
    });
}

- (void)onVerifySuccessWithResult:(T3LoginResult *)result
                             card:(NSString *)card
                        stateCode:(NSString *)stateCode {
    self.card = card;
    self.stateCode = stateCode;
    self.endTime = result.endTime;

    CVLog(@"[主控] 验证通过 → 到期=%@ 时长=%@ 剩余=%@s 核心=%@",
          result.endTime ?: @"(空)",
          result.amount ?: @"-",
          result.available ?: @"-",
          result.core ?: @"-");

    // ② 装覆盖层（到期时间 + 按钮屏蔽）
    [self installOverlay];

    // 心跳保活
    [self startHeartbeat];
}

#pragma mark - ② 覆盖层

/// ★ 用户要求：「如果可以直接hook掉原宿主的到期时间显示真实的不行就覆盖掉显示真实的」
///
///   所以这里分两步走：
///     第一步 —— CVHostHook 直接找到宿主那条 UILabel，改成真实到期
///               （视觉完全融入宿主，最自然）
///     第二步 —— 找不到才退回 CVOverlay 的平面覆盖
///
///   另外：屏蔽按钮这件事无论走哪条路都要做，它挂在 CVOverlay 上。
- (void)installOverlay {
    NSString *shown = self.endTime.length > 0 ? [self shortDate:self.endTime] : @"未知";

    // ── 第一步：尝试直改宿主标签 ──
    BOOL hooked = NO;
    @try {
        hooked = [CVHostHook applyExpiryText:shown];
    } @catch (NSException *e) {
        CVLog(@"[宿主直改] 抛异常，退回覆盖：%@", e.reason);
        hooked = NO;
    }

    // ── 第二步：覆盖层 ──
    //   无论 hook 成没成，都要挂 overlay —— 因为它还负责屏蔽 6 个按钮。
    //   区别只在于：hook 成功时 overlay 不再画那条到期胶囊（避免双份）。
    if (!self.overlay) {
        self.overlay = [[CVOverlay alloc] init];
    }
    self.overlay.expiryText = hooked ? nil : shown;   // nil → 不画胶囊
    [self.overlay attachToWindow];

    if (hooked) {
        CVLog(@"[主控] 到期时间走【直改宿主标签】：「%@」", shown);
        // 宿主可能定时刷新自己的文案，开个守护持续纠正
        [CVHostHook startKeepAliveWithExpiry:shown];
    } else {
        CVLog(@"[主控] 到期时间走【覆盖层】：「%@」", shown);
    }

    // 诊断信息（排错时很有用）
    [CVHostHook logCandidates];
}

/// 把 "2025-06-30 12:00:00" 之类裁成显示用的短串
- (NSString *)shortDate:(NSString *)raw {
    if (raw.length <= 19) return raw;
    return [raw substringToIndex:19];
}

#pragma mark - ③ 心跳

- (void)startHeartbeat {
    [self.heartbeatTimer invalidate];
    self.heartbeatFail = 0;
    self.heartbeatTimer = [NSTimer scheduledTimerWithTimeInterval:kCVHeartbeatInterval
                                                          target:self
                                                        selector:@selector(doHeartbeat)
                                                        userInfo:nil
                                                         repeats:YES];
    CVLog(@"[心跳] 已启动，间隔 %.0fs，连续失败 %d 次处理", kCVHeartbeatInterval, kCVMaxHeartbeatFail);
}

- (void)doHeartbeat {
    if (self.card.length == 0) return;
    NSString *card = self.card, *sc = self.stateCode;

    __weak typeof(self) weakSelf = self;
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        T3Result *r = nil;
        @try {
            r = [weakSelf.verifier heartbeatWithKami:card statecode:sc];
        } @catch (NSException *e) {
            r = [T3Result fail:@"心跳异常"];
        }
        dispatch_async(dispatch_get_main_queue(), ^{
            typeof(self) self = weakSelf;
            if (!self) return;
            if (r && r.success) {
                if (self.heartbeatFail > 0) CVLog(@"[心跳] ✅ 恢复正常");
                self.heartbeatFail = 0;
            } else {
                self.heartbeatFail++;
                CVLog(@"[心跳] ❌ 失败 %d/%d : %@",
                      self.heartbeatFail, kCVMaxHeartbeatFail, r.error ?: @"未知");
                if (self.heartbeatFail >= kCVMaxHeartbeatFail) {
                    [self.heartbeatTimer invalidate];
                    CVLog(@"[心跳] 达到上限，清除本地卡密并要求重新验证");
                    [[NSUserDefaults standardUserDefaults] removeObjectForKey:kCVPrefSavedCard];
                    [[NSUserDefaults standardUserDefaults] synchronize];
                    self.didShowPanel = NO;
                    [self presentPanel];
                }
            }
        });
    });
}

#pragma mark - 工具

- (UIWindow *)keyWindow {
    UIWindow *found = nil;
    if (@available(iOS 13.0, *)) {
        for (UIScene *scene in [UIApplication sharedApplication].connectedScenes) {
            if (![scene isKindOfClass:[UIWindowScene class]]) continue;
            UIWindowScene *ws = (UIWindowScene *)scene;
            for (UIWindow *w in ws.windows) {
                if (w.isKeyWindow) return w;
            }
            if (!found && ws.windows.count > 0) found = ws.windows.firstObject;
        }
    }
    if (!found) found = [UIApplication sharedApplication].keyWindow;
    return found;
}

@end

// ══════════════════════════════════════════════════════════════════════════
//  dylib 入口 —— constructor，注入即执行
// ══════════════════════════════════════════════════════════════════════════

__attribute__((constructor))
static void CoreVerifyEntry(void) {
    @autoreleasepool {
        CVLog(@"────────────────────────────────────────────");
        CVLog(@"CoreVerify dylib 已加载");
        CVLog(@"  bundle = %@", [[NSBundle mainBundle] bundleIdentifier]);
        CVLog(@"  进程   = %@", [[NSProcessInfo processInfo] processName]);
        CVLog(@"  iOS    = %@", [[UIDevice currentDevice] systemVersion]);
        CVLog(@"  机型   = %@", [[UIDevice currentDevice] model]);

        // ★ 只在宿主进程里干活：
        //    自签重打包后 bundle id 可能被改，所以不硬卡 bundle id，
        //    改成"有 UIKit + 有可执行文件"就放行，并把实际值记进日志。
        NSString *bid = [[NSBundle mainBundle] bundleIdentifier] ?: @"";
        if ([bid hasPrefix:@"com.apple."]) {
            CVLog(@"检测到系统进程（%@），不注入", bid);
            return;
        }

        dispatch_async(dispatch_get_main_queue(), ^{
            [[CoreVerify shared] start];
        });
    }
}
