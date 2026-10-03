//
//  CVLog.h —— 统一日志
//
//  输出到三处：
//    1. NSLog（连接 Xcode / idevicesyslog 能看到）
//    2. 应用沙盒 Documents/CoreVerify.log（自签环境 get-task-allow=False 时的唯一途径）
//
//  ★ 自签重打包时 get-task-allow 通常是 false，NSLog 抓不到，
//    所以必须落地到文件，用户可以用 Filza / 文件App 打开查看。
//

#ifndef CVLog_h
#define CVLog_h

#import <Foundation/Foundation.h>

/// 日志开关：0 = 只写文件，1 = 同时 NSLog，2 = 更详细
#ifndef CV_LOG_LEVEL
#define CV_LOG_LEVEL 1
#endif

/// 日志文件路径（沙盒 Documents/CoreVerify.log）
FOUNDATION_EXPORT NSString *CVLogFilePath(void);

/// 主日志函数。用法：CVLog(@"[模块] 内容 %d", n)
FOUNDATION_EXPORT void CVLog(NSString *fmt, ...) NS_FORMAT_FUNCTION(1, 2);

/// 超长内容分块写（比如反汇编/长 JSON）
FOUNDATION_EXPORT void CVLogBlock(NSString *tag, NSString *content);

#endif /* CVLog_h */
