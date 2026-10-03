//
//  CVLog.m —— 统一日志实现
//
//  线程安全：用 dispatch_queue 串行化写文件，避免多线程交叉写坏日志。
//  滚动：文件超过 512KB 时截断保留后一半，防止无限增长。
//

#import "CVLog.h"
#import <UIKit/UIKit.h>

static dispatch_queue_t gCVLogQueue(void) {
    static dispatch_queue_t q;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        q = dispatch_queue_create("com.coreverify.log", DISPATCH_QUEUE_SERIAL);
    });
    return q;
}

NSString *CVLogFilePath(void) {
    static NSString *path;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        NSArray *docs = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,
                                                            NSUserDomainMask, YES);
        NSString *dir = docs.count > 0 ? docs[0] : NSTemporaryDirectory();
        path = [dir stringByAppendingPathComponent:@"CoreVerify.log"];
    });
    return path;
}

/// 文件超过 512KB → 保留后半段
static void CVLogRotateIfNeeded(void) {
    NSString *p = CVLogFilePath();
    NSFileManager *fm = [NSFileManager defaultManager];
    NSDictionary *attr = [fm attributesOfItemAtPath:p error:nil];
    unsigned long long sz = [attr fileSize];
    if (sz < 512 * 1024) return;

    NSData *d = [NSData dataWithContentsOfFile:p];
    if (d.length > 256 * 1024) {
        NSData *tail = [d subdataWithRange:NSMakeRange(d.length - 256 * 1024, 256 * 1024)];
        [tail writeToFile:p atomically:YES];
    } else {
        [fm removeItemAtPath:p error:nil];
    }
}

void CVLog(NSString *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    NSString *body = [[NSString alloc] initWithFormat:fmt arguments:args];
    va_end(args);

    if (!body) return;

    // 时间戳（用本地时区，方便和界面对照）
    static NSDateFormatter *df;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        df = [[NSDateFormatter alloc] init];
        df.dateFormat = @"HH:mm:ss.SSS";
    });
    NSString *ts = [df stringFromDate:[NSDate date]];
    NSString *line = [NSString stringWithFormat:@"[%@] %@\n", ts, body];

#if CV_LOG_LEVEL >= 1
    // NSLog 走 stderr，Xcode / idevicesyslog 可见
    fputs([[NSString stringWithFormat:@"[CV] %@", line] UTF8String], stderr);
#endif

    dispatch_async(gCVLogQueue(), ^{
        CVLogRotateIfNeeded();
        NSString *p = CVLogFilePath();
        NSFileHandle *fh = [NSFileHandle fileHandleForWritingAtPath:p];
        if (!fh) {
            [line writeToFile:p atomically:YES encoding:NSUTF8StringEncoding error:nil];
        } else {
            @try {
                [fh seekToEndOfFile];
                [fh writeData:[line dataUsingEncoding:NSUTF8StringEncoding]];
                [fh closeFile];
            } @catch (NSException *e) {
                // 写日志本身绝不能抛异常影响主流程
            }
        }
    });
}

void CVLogBlock(NSString *tag, NSString *content) {
    if (!content) return;
    NSArray<NSString *> *lines = [content componentsSeparatedByString:@"\n"];
    for (NSString *ln in lines) {
        CVLog(@"[%@] %@", tag, ln);
    }
}
