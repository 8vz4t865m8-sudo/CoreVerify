#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 iOS SDK 的最小 stub 头，让 clang 能在 Linux 上对 Objective-C 源码
做 -fsyntax-only 检查。

★ 这不是完整 SDK，只求"类型和签名对得上，能过语法分析"。
★ 目的：在沙盒里抓出 漏分号 / 括号不配对 / @end 缺失 / 方法签名不匹配
   这类真实编译错误 —— 这些是 CI 上最常见的失败原因。
"""

import os

ROOT = "/tmp/cvstub"

FILES = {}

# ── 基础几何类型（Foundation 与 CoreGraphics 都要用，先独立出来）──
# ★ 真实 iOS SDK 里这些定义在 CoreGraphics 的 CGBase.h，
#   Foundation.h 会间接引入。我们的 stub 里必须保证「先定义后使用」。
FILES["CVGeom.h"] = r'''
#pragma once
/* 基础数值与几何类型 —— 供 Foundation / CoreGraphics / UIKit 共用 */
typedef unsigned char BOOL;
#ifndef YES
#define YES ((BOOL)1)
#endif
#ifndef NO
#define NO ((BOOL)0)
#endif
typedef float CGFloat;
typedef double NSTimeInterval;

typedef struct CGPoint { CGFloat x, y; } CGPoint;
typedef struct CGSize  { CGFloat width, height; } CGSize;
typedef struct CGRect  { CGPoint origin; CGSize size; } CGRect;
typedef struct CGVector { CGFloat dx, dy; } CGVector;
typedef struct CGAffineTransform { CGFloat a,b,c,d,tx,ty; } CGAffineTransform;
typedef struct CATransform3D {
    CGFloat m11,m12,m13,m14, m21,m22,m23,m24,
            m31,m32,m33,m34, m41,m42,m43,m44;
} CATransform3D;
typedef struct CGColor *CGColorRef;
typedef struct CGPath  *CGPathRef;
typedef struct CGImage *CGImageRef;

typedef struct UIEdgeInsets { CGFloat top, left, bottom, right; } UIEdgeInsets;

#define CGPointMake(x,y)    ((CGPoint){(CGFloat)(x),(CGFloat)(y)})
#define CGSizeMake(w,h)     ((CGSize){(CGFloat)(w),(CGFloat)(h)})
#define CGRectMake(x,y,w,h) ((CGRect){{(CGFloat)(x),(CGFloat)(y)},{(CGFloat)(w),(CGFloat)(h)}})
#define CGPointZero ((CGPoint){0,0})
#define CGSizeZero  ((CGSize){0,0})
#define CGRectZero  ((CGRect){{0,0},{0,0}})
#define CGRectNull  ((CGRect){{0,0},{0,0}})
#define UIEdgeInsetsMake(t,l,b,r) ((UIEdgeInsets){(CGFloat)(t),(CGFloat)(l),(CGFloat)(b),(CGFloat)(r)})
#define UIEdgeInsetsZero ((UIEdgeInsets){0,0,0,0})
#define CGAffineTransformIdentity ((CGAffineTransform){1,0,0,1,0,0})
#define CGAffineTransformMakeScale(sx,sy) ((CGAffineTransform){(CGFloat)(sx),0,0,(CGFloat)(sy),0,0})
#define CGAffineTransformMakeRotation(a)  ((CGAffineTransform){1,0,0,1,0,0})
#define CGAffineTransformTranslate(t,dx,dy) (t)
#define CGAffineTransformRotate(t,a)        (t)
#define CGAffineTransformScale(t,sx,sy)     (t)
#define CATransform3DIdentity ((CATransform3D){1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1})
#define CATransform3DMakeRotation(a,x,y,z) (CATransform3DIdentity)
#define CATransform3DMakeScale(sx,sy,sz)   (CATransform3DIdentity)

extern CGRect  CGRectInset(CGRect r, CGFloat dx, CGFloat dy);
extern CGRect  CGRectOffset(CGRect r, CGFloat dx, CGFloat dy);
extern CGRect  CGRectIntersection(CGRect a, CGRect b);
extern CGRect  CGRectUnion(CGRect a, CGRect b);
extern CGRect  CGRectIntegral(CGRect r);
extern CGRect  CGRectStandardize(CGRect r);
extern BOOL    CGRectContainsPoint(CGRect r, CGPoint p);
extern BOOL    CGRectContainsRect(CGRect a, CGRect b);
extern BOOL    CGRectIntersectsRect(CGRect a, CGRect b);
extern BOOL    CGRectIsEmpty(CGRect r);
extern BOOL    CGRectEqualToRect(CGRect a, CGRect b);
extern BOOL    CGPointEqualToPoint(CGPoint a, CGPoint b);
extern BOOL    CGSizeEqualToSize(CGSize a, CGSize b);
extern CGFloat CGRectGetMinX(CGRect r);
extern CGFloat CGRectGetMidX(CGRect r);
extern CGFloat CGRectGetMaxX(CGRect r);
extern CGFloat CGRectGetMinY(CGRect r);
extern CGFloat CGRectGetMidY(CGRect r);
extern CGFloat CGRectGetMaxY(CGRect r);
extern CGFloat CGRectGetWidth(CGRect r);
extern CGFloat CGRectGetHeight(CGRect r);
'''

# ── Foundation/Foundation.h ──
FILES["Foundation/Foundation.h"] = r'''
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "CVGeom.h"
#include "dispatch/dispatch.h"

/* ★ TargetConditionals —— 决定源码走 iOS 分支还是 macOS 分支。
   真实 iOS SDK 里由 <TargetConditionals.h> 提供。
   这里必须显式定义，否则 #if TARGET_OS_IOS 会当 0，
   让 T3Verify.m 走进 IOKit 分支，在 Linux 上编译不过。 */
#define TARGET_OS_IOS     1
#define TARGET_OS_IPHONE  1
#define TARGET_OS_MAC     0
#define TARGET_OS_OSX     0
#define TARGET_OS_SIMULATOR 0
#define TARGET_OS_EMBEDDED 1
#define TARGET_OS_TV      0
#define TARGET_OS_WATCH   0
#define TARGET_OS_MACCATALYST 0
#define TARGET_CPU_ARM64  1
#define TARGET_CPU_ARM64E 1

#define NS_ASSUME_NONNULL_BEGIN
#define NS_ASSUME_NONNULL_END
#define NS_FORMAT_FUNCTION(a,b)
#define FOUNDATION_EXPORT extern
#define NS_ENUM(_t,_n) enum _n : _t
#define NS_OPTIONS(_t,_n) enum _n : _t

#ifndef nil
#define nil ((id)0)
#endif
#ifndef NULL
#define NULL ((void*)0)
#endif

typedef long NSInteger;
typedef unsigned long NSUInteger;
typedef unsigned short unichar;

@class NSString, NSMutableString, NSArray, NSMutableArray, NSDictionary, NSMutableDictionary;
@class NSError, NSException, NSData, NSMutableData, NSNumber, NSValue, NSDate;
@class NSUserDefaults, NSDateFormatter, NSTimer, NSNotification, NSNotificationCenter;
@class NSFileManager, NSFileHandle, NSBundle, NSProcessInfo, NSObject;
@class NSAttributedString, NSMutableAttributedString, NSCharacterSet, NSIndexSet;
@class NSSet, NSMutableSet, NSOrderedSet, NSURL, NSURLRequest, NSMutableURLRequest;
@class NSURLSession, NSURLSessionDataTask, NSHTTPURLResponse, NSURLResponse;
@class NSJSONSerialization, NSRegularExpression, NSTextCheckingResult;
@class NSInvocation, NSMethodSignature, NSRunLoop, NSThread, NSLock;
@class NSCondition, NSRecursiveLock, NSUUID, NSUserNotification, NSValueTransformer;
@class NSTimeZone, NSLocale, NSIndexPath, NSSortDescriptor, NSPredicate, NSNumberFormatter;
@class NSHTTPCookie, NSURLCredential, NSURLCache, NSURLSessionConfiguration;

/* ★ NSRange 必须在使用它的 NSString 之前定义 */
typedef struct _NSRange { NSUInteger location, length; } NSRange;
FOUNDATION_EXPORT NSRange NSMakeRange(NSUInteger loc, NSUInteger len);
FOUNDATION_EXPORT const NSRange NSRangeZero;
#define NSNotFound ((NSInteger)0x7fffffffffffffffL)

@protocol NSObject
- (BOOL)isEqual:(id)o;
- (NSUInteger)hash;
- (Class)class;
- (BOOL)respondsToSelector:(SEL)s;
- (id)performSelector:(SEL)s;
- (id)performSelector:(SEL)s withObject:(id)o;
- (id)performSelector:(SEL)s withObject:(id)a withObject:(id)b;
- (BOOL)isKindOfClass:(Class)c;
- (BOOL)isMemberOfClass:(Class)c;
- (BOOL)conformsToProtocol:(Protocol *)p;
- (NSString *)description;
- (NSString *)debugDescription;
- (instancetype)self;
- (instancetype)retain;
- (oneway void)release;
- (instancetype)autorelease;
- (NSUInteger)retainCount;
- (BOOL)isProxy;
@end

@protocol NSCopying
- (id)copyWithZone:(void *)zone;
@end

@interface NSObject <NSObject>
+ (instancetype)alloc;
+ (instancetype)new;
+ (Class)class;
+ (BOOL)instancesRespondToSelector:(SEL)s;
+ (BOOL)conformsToProtocol:(Protocol *)p;
+ (NSString *)description;
- (instancetype)init;
- (void)dealloc;
- (id)copy;
- (id)mutableCopy;
- (void)forwardInvocation:(NSInvocation *)i;
- (NSMethodSignature *)methodSignatureForSelector:(SEL)s;
- (id)valueForKey:(NSString *)k;
- (void)setValue:(id)v forKey:(NSString *)k;
@end

@interface NSValue : NSObject
+ (NSValue *)valueWithPointer:(const void *)p;
+ (NSValue *)valueWithCGRect:(CGRect)r;
+ (NSValue *)valueWithCGPoint:(CGPoint)p;
+ (NSValue *)valueWithCGSize:(CGSize)s;
+ (NSValue *)valueWithInt:(int)i;
+ (NSValue *)valueWithBool:(BOOL)b;
+ (NSValue *)valueWithInteger:(NSInteger)i;
- (CGRect)CGRectValue;
- (CGPoint)CGPointValue;
- (CGSize)CGSizeValue;
- (int)intValue;
- (BOOL)boolValue;
- (NSInteger)integerValue;
@end

@interface NSString : NSObject <NSCopying>
@property (nonatomic, readonly) NSUInteger length;
+ (instancetype)string;
+ (instancetype)stringWithString:(NSString *)s;
+ (instancetype)stringWithFormat:(NSString *)f, ...;
- (instancetype)initWithFormat:(NSString *)f, ...;
- (instancetype)initWithFormat:(NSString *)f arguments:(va_list)a;
+ (instancetype)stringWithUTF8String:(const char *)c;
+ (instancetype)stringWithContentsOfFile:(NSString *)p encoding:(NSUInteger)e error:(NSError **)err;
+ (instancetype)stringWithCharacters:(const unsigned short *)c length:(NSUInteger)l;
+ (instancetype)stringWithCapacity:(NSUInteger)c;
- (const char *)UTF8String;
- (const char *)fileSystemRepresentation;
- (BOOL)isEqualToString:(NSString *)s;
- (BOOL)hasPrefix:(NSString *)s;
- (BOOL)hasSuffix:(NSString *)s;
- (NSString *)lowercaseString;
- (NSString *)uppercaseString;
- (NSString *)stringByTrimmingCharactersInSet:(NSCharacterSet *)cs;
- (NSString *)stringByAppendingString:(NSString *)s;
- (NSString *)stringByAppendingFormat:(NSString *)f, ...;
- (NSString *)stringByAppendingPathComponent:(NSString *)p;
- (NSString *)stringByDeletingPathExtension;
- (NSString *)stringByReplacingOccurrencesOfString:(NSString *)a withString:(NSString *)b;
- (NSString *)substringFromIndex:(NSUInteger)i;
- (NSString *)substringToIndex:(NSUInteger)i;
- (NSString *)substringWithRange:(NSRange)r;
- (NSRange)rangeOfString:(NSString *)s;
- (NSRange)rangeOfString:(NSString *)s options:(NSUInteger)o;
- (NSRange)rangeOfString:(NSString *)s options:(NSUInteger)o range:(NSRange)r;
- (NSRange)rangeOfCharacterFromSet:(NSCharacterSet *)cs;
- (NSArray *)componentsSeparatedByString:(NSString *)s;
- (NSArray *)componentsSeparatedByCharactersInSet:(NSCharacterSet *)cs;
- (NSArray *)componentsJoinedByString:(NSString *)s;
- (double)doubleValue;
- (float)floatValue;
- (int)intValue;
- (NSInteger)integerValue;
- (long long)longLongValue;
- (BOOL)boolValue;
- (unichar)characterAtIndex:(NSUInteger)i;
- (NSData *)dataUsingEncoding:(NSUInteger)e;
- (instancetype)initWithData:(NSData *)d encoding:(NSUInteger)e;
- (instancetype)initWithUTF8String:(const char *)c;
- (instancetype)initWithString:(NSString *)s;
- (NSString *)stringByAddingPercentEncodingWithAllowedCharacters:(NSCharacterSet *)cs;
- (NSString *)stringByReplacingCharactersInRange:(NSRange)r withString:(NSString *)s;
- (BOOL)writeToFile:(NSString *)p atomically:(BOOL)a encoding:(NSUInteger)e error:(NSError **)err;
- (BOOL)writeToFile:(NSString *)p atomically:(BOOL)a;
- (BOOL)writeToURL:(NSURL *)u atomically:(BOOL)a encoding:(NSUInteger)e error:(NSError **)err;
@end

@interface NSMutableString : NSString
+ (instancetype)stringWithCapacity:(NSUInteger)c;
- (void)appendString:(NSString *)s;
- (void)appendFormat:(NSString *)f, ...;
- (void)insertString:(NSString *)s atIndex:(NSUInteger)i;
@end

@interface NSArray<__covariant ObjectType> : NSObject
@property (nonatomic, readonly) NSUInteger count;
@property (nonatomic, readonly) id firstObject;
@property (nonatomic, readonly) id lastObject;
+ (instancetype)array;
+ (instancetype)arrayWithObject:(id)o;
+ (instancetype)arrayWithObjects:(const id *)o count:(NSUInteger)c;
+ (instancetype)arrayWithArray:(NSArray *)a;
- (ObjectType)objectAtIndex:(NSUInteger)i;
- (ObjectType)objectAtIndexedSubscript:(NSUInteger)i;
- (NSUInteger)indexOfObject:(id)o;
- (BOOL)containsObject:(id)o;
- (void)enumerateObjectsUsingBlock:(void (^)(id o, NSUInteger i, BOOL *stop))b;
- (NSString *)componentsJoinedByString:(NSString *)s;
- (id)firstObjectCommonWithArray:(NSArray *)a;
@end

@interface NSMutableArray<ObjectType> : NSArray<ObjectType>
+ (instancetype)arrayWithCapacity:(NSUInteger)c;
- (void)addObject:(id)o;
- (void)addObjectsFromArray:(NSArray *)a;
- (void)insertObject:(id)o atIndex:(NSUInteger)i;
- (void)removeObject:(id)o;
- (void)removeObjectAtIndex:(NSUInteger)i;
- (void)removeAllObjects;
- (void)removeLastObject;
- (void)replaceObjectAtIndex:(NSUInteger)i withObject:(id)o;
- (void)exchangeObjectAtIndex:(NSUInteger)a withObjectAtIndex:(NSUInteger)b;
- (void)setObject:(id)o atIndexedSubscript:(NSUInteger)i;
@end

@interface NSDictionary<__covariant KeyType, __covariant ObjectType> : NSObject
@property (nonatomic, readonly) NSUInteger count;
@property (nonatomic, readonly) NSArray *allKeys;
@property (nonatomic, readonly) NSArray *allValues;
+ (instancetype)dictionary;
+ (instancetype)dictionaryWithObject:(id)o forKey:(id)k;
+ (instancetype)dictionaryWithObjects:(const id *)o forKeys:(const id *)k count:(NSUInteger)c;
+ (instancetype)dictionaryWithObjectsAndKeys:(id)first, ...;
- (id)objectForKey:(id)k;
- (id)objectForKeyedSubscript:(id)k;
- (BOOL)writeToFile:(NSString *)p atomically:(BOOL)a;
@end

@interface NSDictionary (NSFileAttributes)
- (unsigned long long)fileSize;
- (NSDate *)fileModificationDate;
@end

@interface NSMutableDictionary<KeyType, ObjectType> : NSDictionary<KeyType, ObjectType>
+ (instancetype)dictionaryWithCapacity:(NSUInteger)c;
- (void)setObject:(id)o forKey:(id)k;
- (void)setObject:(id)o forKeyedSubscript:(id)k;
- (void)removeObjectForKey:(id)k;
- (void)removeAllObjects;
@end

@interface NSSet<__covariant ObjectType> : NSObject
+ (instancetype)setWithArray:(NSArray *)a;
- (BOOL)containsObject:(id)o;
@end

@interface NSCharacterSet : NSObject
+ (NSCharacterSet *)whitespaceAndNewlineCharacterSet;
+ (NSCharacterSet *)whitespaceCharacterSet;
+ (NSCharacterSet *)decimalDigitCharacterSet;
+ (NSCharacterSet *)alphanumericCharacterSet;
- (NSCharacterSet *)invertedSet;
+ (NSCharacterSet *)characterSetWithCharactersInString:(NSString *)s;
+ (NSCharacterSet *)URLQueryAllowedCharacterSet;
+ (NSCharacterSet *)URLHostAllowedCharacterSet;
+ (NSCharacterSet *)URLPathAllowedCharacterSet;
+ (NSCharacterSet *)URLFragmentAllowedCharacterSet;
@end

@interface NSNumber : NSObject
+ (NSNumber *)numberWithInt:(int)i;
+ (NSNumber *)numberWithInteger:(NSInteger)i;
+ (NSNumber *)numberWithUnsignedInt:(unsigned)i;
+ (NSNumber *)numberWithUnsignedInteger:(NSUInteger)i;
+ (NSNumber *)numberWithBool:(BOOL)b;
+ (NSNumber *)numberWithDouble:(double)d;
+ (NSNumber *)numberWithLongLong:(long long)v;
+ (NSNumber *)numberWithUnsignedLong:(unsigned long)v;
+ (NSNumber *)numberWithUnsignedLongLong:(unsigned long long)v;
+ (NSNumber *)numberWithChar:(char)v;
+ (NSNumber *)numberWithShort:(short)v;
+ (NSNumber *)numberWithUnsignedShort:(unsigned short)v;
+ (NSNumber *)numberWithFloat:(float)v;
+ (NSNumber *)numberWithLong:(long)v;
- (int)intValue;
- (NSInteger)integerValue;
- (unsigned)unsignedIntValue;
- (BOOL)boolValue;
- (double)doubleValue;
- (long long)longLongValue;
- (NSString *)stringValue;
@end

@interface NSData : NSObject
@property (nonatomic, readonly) NSUInteger length;
@property (nonatomic, readonly) const void *bytes;
+ (instancetype)data;
+ (instancetype)dataWithBytes:(const void *)b length:(NSUInteger)l;
+ (instancetype)dataWithLength:(NSUInteger)l;
+ (instancetype)dataWithContentsOfFile:(NSString *)p;
+ (instancetype)dataWithData:(NSData *)d;
- (NSData *)subdataWithRange:(NSRange)r;
- (void)getBytes:(void *)buf length:(NSUInteger)l;
- (void)getBytes:(void *)buf range:(NSRange)r;
- (BOOL)writeToFile:(NSString *)p atomically:(BOOL)a;
- (NSString *)base64EncodedStringWithOptions:(NSUInteger)o;
- (instancetype)initWithBase64EncodedString:(NSString *)s options:(NSUInteger)o;
- (instancetype)initWithBytes:(const void *)b length:(NSUInteger)l;
- (instancetype)initWithData:(NSData *)d;
@end

@interface NSMutableData : NSData
+ (instancetype)dataWithCapacity:(NSUInteger)c;
+ (instancetype)dataWithLength:(NSUInteger)l;
- (void)appendBytes:(const void *)b length:(NSUInteger)l;
- (void)appendData:(NSData *)d;
- (void *)mutableBytes;
- (void)setLength:(NSUInteger)l;
@end

@interface NSError : NSObject
@property (nonatomic, readonly) NSInteger code;
@property (nonatomic, readonly) NSString *domain;
@property (nonatomic, readonly) NSString *localizedDescription;
@property (nonatomic, readonly) NSDictionary *userInfo;
+ (instancetype)errorWithDomain:(NSString *)d code:(NSInteger)c userInfo:(NSDictionary *)u;
@end

@interface NSException : NSObject
@property (nonatomic, readonly) NSString *name;
@property (nonatomic, readonly) NSString *reason;
@property (nonatomic, readonly) NSDictionary *userInfo;
+ (instancetype)exceptionWithName:(NSString *)n reason:(NSString *)r userInfo:(NSDictionary *)u;
+ (void)raise:(NSString *)n format:(NSString *)f, ...;
- (void)raise;
@end

@interface NSDate : NSObject
+ (instancetype)date;
+ (instancetype)dateWithTimeIntervalSince1970:(NSTimeInterval)t;
- (NSTimeInterval)timeIntervalSince1970;
- (NSTimeInterval)timeIntervalSinceNow;
- (NSInteger)timeIntervalSinceDate:(NSDate *)d;
- (BOOL)isEqualToDate:(NSDate *)d;
@end

@interface NSTimeZone : NSObject
+ (NSTimeZone *)systemTimeZone;
+ (NSTimeZone *)timeZoneForSecondsFromGMT:(NSInteger)s;
+ (NSTimeZone *)timeZoneWithAbbreviation:(NSString *)a;
+ (NSTimeZone *)timeZoneWithName:(NSString *)n;
@property (nonatomic, readonly) NSString *name;
@property (nonatomic, readonly) NSInteger secondsFromGMT;
@end

@interface NSLocale : NSObject
+ (NSLocale *)currentLocale;
+ (NSLocale *)localeWithLocaleIdentifier:(NSString *)i;
@end

@interface NSNumberFormatter : NSObject
@property (nonatomic) NSInteger numberStyle;
- (NSString *)stringFromNumber:(NSNumber *)n;
- (NSNumber *)numberFromString:(NSString *)s;
@end

@interface NSDateFormatter : NSObject
@property (nonatomic, copy) NSString *dateFormat;
@property (nonatomic, copy) NSString *timeZone;
@property (nonatomic, copy) NSString *locale;
+ (instancetype)localTimeZone;
+ (instancetype)timeZoneWithName:(NSString *)n;
+ (instancetype)localeWithLocaleIdentifier:(NSString *)n;
- (NSString *)stringFromDate:(NSDate *)d;
- (NSDate *)dateFromString:(NSString *)s;
@end

@interface NSUserDefaults : NSObject
+ (NSUserDefaults *)standardUserDefaults;
- (id)objectForKey:(NSString *)k;
- (NSString *)stringForKey:(NSString *)k;
- (NSInteger)integerForKey:(NSString *)k;
- (BOOL)boolForKey:(NSString *)k;
- (void)setObject:(id)o forKey:(NSString *)k;
- (void)setInteger:(NSInteger)i forKey:(NSString *)k;
- (void)setBool:(BOOL)b forKey:(NSString *)k;
- (void)removeObjectForKey:(NSString *)k;
- (BOOL)synchronize;
@end

@interface NSTimer : NSObject
+ (NSTimer *)scheduledTimerWithTimeInterval:(NSTimeInterval)t
                                     target:(id)target
                                   selector:(SEL)sel
                                   userInfo:(id)info
                                    repeats:(BOOL)rep;
+ (NSTimer *)timerWithTimeInterval:(NSTimeInterval)t
                            target:(id)target
                          selector:(SEL)sel
                          userInfo:(id)info
                           repeats:(BOOL)rep;
- (void)invalidate;
- (void)fire;
@property (nonatomic, readonly) BOOL isValid;
@property (nonatomic) NSTimeInterval tolerance;
@end

@interface NSNotification : NSObject
@property (nonatomic, readonly) NSString *name;
@property (nonatomic, readonly) id object;
@property (nonatomic, readonly) NSDictionary *userInfo;
@end

@interface NSNotificationCenter : NSObject
+ (NSNotificationCenter *)defaultCenter;
- (void)addObserver:(id)o selector:(SEL)s name:(NSString *)n object:(id)obj;
- (id)addObserverForName:(NSString *)n
                   object:(id)obj
                    queue:(id)q
               usingBlock:(void (^)(NSNotification *note))b;
- (void)removeObserver:(id)o;
- (void)removeObserver:(id)o name:(NSString *)n object:(id)obj;
- (void)postNotificationName:(NSString *)n object:(id)o;
- (void)postNotificationName:(NSString *)n object:(id)o userInfo:(NSDictionary *)u;
@end

FOUNDATION_EXPORT NSString * const NSForegroundColorAttributeName;
FOUNDATION_EXPORT NSString * const NSFontAttributeName;
FOUNDATION_EXPORT NSString * const NSBackgroundColorAttributeName;
FOUNDATION_EXPORT NSString * const NSLocalizedDescriptionKey;
FOUNDATION_EXPORT NSString * const NSFileModificationDate;
FOUNDATION_EXPORT NSString * const NSFileSize;
FOUNDATION_EXPORT NSString * const NSUTF8StringEncoding;
FOUNDATION_EXPORT NSString * const NSASCIIStringEncoding;
FOUNDATION_EXPORT NSString * const NSDocumentDirectory;
FOUNDATION_EXPORT NSString * const NSUserDomainMask;
FOUNDATION_EXPORT NSString * const NSCachesDirectory;
FOUNDATION_EXPORT NSString * const NSLocaleIdentifier;
FOUNDATION_EXPORT NSString * const NSTimeZoneNameStyleStandard;
FOUNDATION_EXPORT NSString * const NSRunLoopCommonModes;
FOUNDATION_EXPORT NSString * const NSDefaultRunLoopMode;
FOUNDATION_EXPORT NSString * const NSURLErrorDomain;

@interface NSAttributedString : NSObject
+ (instancetype)alloc;
- (instancetype)initWithString:(NSString *)s;
- (instancetype)initWithString:(NSString *)s attributes:(NSDictionary *)a;
- (instancetype)initWithAttributedString:(NSAttributedString *)a;
@property (nonatomic, readonly) NSString *string;
@property (nonatomic, readonly) NSUInteger length;
@end

@interface NSMutableAttributedString : NSAttributedString
- (void)addAttribute:(NSString *)name value:(id)v range:(NSRange)r;
- (void)addAttributes:(NSDictionary *)a range:(NSRange)r;
- (void)setAttributes:(NSDictionary *)a range:(NSRange)r;
- (void)appendAttributedString:(NSAttributedString *)s;
- (void)replaceCharactersInRange:(NSRange)r withString:(NSString *)s;
@end

@interface NSURL : NSObject
@property (nonatomic, readonly) NSString *absoluteString;
@property (nonatomic, readonly) NSString *path;
@property (nonatomic, readonly) NSString *scheme;
@property (nonatomic, readonly) NSString *query;
@property (nonatomic, readonly) NSString *host;
@property (nonatomic, readonly) NSNumber *port;
@property (nonatomic, readonly) NSString *absoluteString_;
- (instancetype)initWithString:(NSString *)s;
+ (instancetype)URLWithString:(NSString *)s;
+ (instancetype)fileURLWithPath:(NSString *)p;
@end

@interface NSURLRequest : NSObject
+ (instancetype)requestWithURL:(NSURL *)u;
- (instancetype)initWithURL:(NSURL *)u;
@property (nonatomic, copy) NSString *HTTPMethod;
@property (nonatomic, copy) NSData *HTTPBody;
@property (nonatomic) NSTimeInterval timeoutInterval;
- (void)setValue:(NSString *)v forHTTPHeaderField:(NSString *)f;
@end

@interface NSMutableURLRequest : NSURLRequest
@property (nonatomic, copy) NSString *HTTPMethod;
@property (nonatomic, copy) NSData *HTTPBody;
- (void)setValue:(NSString *)v forHTTPHeaderField:(NSString *)f;
@end

@interface NSURLResponse : NSObject
@property (nonatomic, readonly) NSInteger statusCode;
@property (nonatomic, readonly) NSURL *URL;
@end

@interface NSHTTPURLResponse : NSURLResponse
@property (nonatomic, readonly) NSInteger statusCode;
- (NSString *)valueForHTTPHeaderField:(NSString *)f;
@end

@interface NSURLSessionDataTask : NSObject
- (void)resume;
- (void)cancel;
@end

@interface NSURLSession : NSObject
+ (NSURLSession *)sharedSession;
- (NSURLSessionDataTask *)dataTaskWithRequest:(NSURLRequest *)r
                            completionHandler:(void (^)(NSData *d, NSURLResponse *resp, NSError *e))h;
@end

@interface NSJSONSerialization : NSObject
+ (id)JSONObjectWithData:(NSData *)d options:(NSUInteger)o error:(NSError **)e;
+ (NSData *)dataWithJSONObject:(id)o options:(NSUInteger)o error:(NSError **)e;
@end

@interface NSRegularExpression : NSObject
+ (instancetype)regularExpressionWithPattern:(NSString *)p options:(NSUInteger)o error:(NSError **)e;
- (id)firstMatchInString:(NSString *)s options:(NSUInteger)o range:(NSRange)r;
@end

@interface NSFileManager : NSObject
+ (NSFileManager *)defaultManager;
- (BOOL)fileExistsAtPath:(NSString *)p;
- (BOOL)createDirectoryAtPath:(NSString *)p
  withIntermediateDirectories:(BOOL)i
                   attributes:(NSDictionary *)a
                        error:(NSError **)e;
- (BOOL)removeItemAtPath:(NSString *)p error:(NSError **)e;
- (NSDictionary *)attributesOfItemAtPath:(NSString *)p error:(NSError **)e;
- (NSArray *)contentsOfDirectoryAtPath:(NSString *)p error:(NSError **)e;
- (BOOL)setAttributes:(NSDictionary *)a ofItemAtPath:(NSString *)p error:(NSError **)e;
@end

@interface NSFileHandle : NSObject
+ (instancetype)fileHandleForWritingAtPath:(NSString *)p;
+ (instancetype)fileHandleForReadingAtPath:(NSString *)p;
- (void)seekToEndOfFile;
- (void)writeData:(NSData *)d;
- (NSData *)readDataToEndOfFile;
- (NSData *)readDataOfLength:(NSUInteger)l;
- (void)closeFile;
@end

@interface NSBundle : NSObject
+ (NSBundle *)mainBundle;
+ (NSBundle *)bundleWithPath:(NSString *)p;
@property (nonatomic, readonly) NSString *bundleIdentifier;
@property (nonatomic, readonly) NSString *bundlePath;
@property (nonatomic, readonly) NSString *executablePath;
- (NSString *)pathForResource:(NSString *)n ofType:(NSString *)t;
- (id)objectForInfoDictionaryKey:(NSString *)k;
@end

@interface NSUUID : NSObject
+ (instancetype)UUID;
- (instancetype)initWithUUIDString:(NSString *)s;
- (NSString *)UUIDString;
@end

@class UIDevice;
@interface UIDevice : NSObject
+ (instancetype)currentDevice;
@property (nonatomic, readonly) NSUUID *identifierForVendor;
@property (nonatomic, readonly) NSString *systemVersion;
@property (nonatomic, readonly) NSString *model;
@property (nonatomic, readonly) NSString *name;
@end

@interface NSProcessInfo : NSObject
+ (NSProcessInfo *)processInfo;
@property (nonatomic, readonly) NSString *processName;
@property (nonatomic, readonly) NSDictionary *environment;
@property (nonatomic, readonly) NSArray *arguments;
@end

@interface NSRunLoop : NSObject
+ (NSRunLoop *)currentRunLoop;
+ (NSRunLoop *)mainRunLoop;
- (void)run;
- (void)runUntilDate:(NSDate *)d;
- (BOOL)runMode:(NSString *)m beforeDate:(NSDate *)d;
- (void)addTimer:(NSTimer *)t forMode:(NSString *)m;
@end

FOUNDATION_EXPORT NSArray *NSSearchPathForDirectoriesInDomains(NSUInteger dir, NSUInteger dom, BOOL expand);
FOUNDATION_EXPORT NSString *NSHomeDirectory(void);
FOUNDATION_EXPORT NSString *NSTemporaryDirectory(void);
FOUNDATION_EXPORT NSString *NSStringFromClass(Class c);
FOUNDATION_EXPORT NSString *NSStringFromSelector(SEL s);
FOUNDATION_EXPORT NSString *NSStringFromCGRect(CGRect r);
FOUNDATION_EXPORT NSString *NSStringFromCGPoint(CGPoint p);
FOUNDATION_EXPORT NSString *NSStringFromCGSize(CGSize s);
FOUNDATION_EXPORT SEL NSSelectorFromString(NSString *s);
FOUNDATION_EXPORT Class NSClassFromString(NSString *s);
FOUNDATION_EXPORT id NSProtocolFromString(NSString *s);
FOUNDATION_EXPORT void NSLog(NSString *fmt, ...);
FOUNDATION_EXPORT void NSLogv(NSString *fmt, va_list args);
'''

# ── CoreGraphics ──
# ★ 几何类型已统一在 CVGeom.h，这里只做一次转发，避免重复 typedef 冲突
FILES["CoreGraphics.h"] = r'''
#pragma once
#include "CVGeom.h"
'''
FILES["CoreGraphics/CoreGraphics.h"] = '#pragma once\n#include "../CoreGraphics.h"\n'

# ── objc/runtime.h ──
FILES["objc/runtime.h"] = r'''
#pragma once
#include <stddef.h>
typedef struct objc_class *Class;
typedef struct objc_object *id;
typedef struct objc_selector *SEL;
typedef struct objc_method *Method;
typedef struct objc_ivar *Ivar;
typedef struct objc_property *objc_property_t;
typedef void (*IMP)(void);
typedef struct objc_category *Category;

FOUNDATION_EXPORT id objc_msgSend(id self, SEL op, ...);
FOUNDATION_EXPORT id objc_msgSendSuper(void *super, SEL op, ...);
FOUNDATION_EXPORT Class objc_getClass(const char *name);
FOUNDATION_EXPORT Class objc_lookUpClass(const char *name);
FOUNDATION_EXPORT Class object_getClass(id obj);
FOUNDATION_EXPORT Class class_getSuperclass(Class c);
FOUNDATION_EXPORT const char *class_getName(Class c);
FOUNDATION_EXPORT const char *object_getClassName(id obj);
FOUNDATION_EXPORT Method class_getInstanceMethod(Class c, SEL s);
FOUNDATION_EXPORT Method class_getClassMethod(Class c, SEL s);
FOUNDATION_EXPORT IMP method_getImplementation(Method m);
FOUNDATION_EXPORT IMP class_getMethodImplementation(Class c, SEL s);
FOUNDATION_EXPORT SEL method_getName(Method m);
FOUNDATION_EXPORT void method_exchangeImplementations(Method a, Method b);
FOUNDATION_EXPORT IMP method_setImplementation(Method m, IMP imp);
FOUNDATION_EXPORT BOOL class_addMethod(Class c, SEL s, IMP imp, const char *types);
FOUNDATION_EXPORT BOOL class_replaceMethod(Class c, SEL s, IMP imp, const char *types);
FOUNDATION_EXPORT SEL sel_registerName(const char *name);
FOUNDATION_EXPORT const char *sel_getName(SEL s);
FOUNDATION_EXPORT Ivar class_getInstanceVariable(Class c, const char *name);
FOUNDATION_EXPORT ptrdiff_t ivar_getOffset(Ivar v);
FOUNDATION_EXPORT const char *ivar_getName(Ivar v);
FOUNDATION_EXPORT const char *ivar_getTypeEncoding(Ivar v);
FOUNDATION_EXPORT id object_getIvar(id obj, Ivar ivar);
FOUNDATION_EXPORT void object_setIvar(id obj, Ivar ivar, id value);
FOUNDATION_EXPORT objc_property_t class_getProperty(Class c, const char *name);
FOUNDATION_EXPORT const char *property_getName(objc_property_t p);
FOUNDATION_EXPORT const char *property_getAttributes(objc_property_t p);
FOUNDATION_EXPORT void objc_setAssociatedObject(id object, const void *key, id value, int policy);
FOUNDATION_EXPORT id objc_getAssociatedObject(id object, const void *key);
FOUNDATION_EXPORT void objc_removeAssociatedObjects(id object);
FOUNDATION_EXPORT id objc_getClassList(Class *buffer, int count);
FOUNDATION_EXPORT int objc_getClassListCount(void);
FOUNDATION_EXPORT Class *objc_copyClassList(unsigned int *outCount);
FOUNDATION_EXPORT void objc_disposeClassPair(Class c);
FOUNDATION_EXPORT Protocol *objc_getProtocol(const char *name);
FOUNDATION_EXPORT BOOL class_conformsToProtocol(Class c, Protocol *p);
FOUNDATION_EXPORT Class objc_allocateClassPair(Class super, const char *name, size_t extra);
FOUNDATION_EXPORT void objc_registerClassPair(Class c);
FOUNDATION_EXPORT const char *object_getIvarName(id obj, Ivar ivar);
FOUNDATION_EXPORT BOOL method_returnsObject(Method m);
FOUNDATION_EXPORT id objc_retain(id obj);
FOUNDATION_EXPORT void objc_release(id obj);
FOUNDATION_EXPORT id objc_autorelease(id obj);
FOUNDATION_EXPORT id objc_autoreleaseReturnValue(id obj);
FOUNDATION_EXPORT id objc_retainAutoreleasedReturnValue(id obj);
FOUNDATION_EXPORT void objc_storeStrong(id *loc, id obj);
FOUNDATION_EXPORT void objc_enumerationMutation(id obj);
FOUNDATION_EXPORT Class _Nullable objc_getRequiredClass(const char *name);
FOUNDATION_EXPORT int objc_sync_enter(id obj);
FOUNDATION_EXPORT int objc_sync_exit(id obj);

#define OBJC_ASSOCIATION_ASSIGN 0
#define OBJC_ASSOCIATION_RETAIN_NONATOMIC 1
#define OBJC_ASSOCIATION_COPY_NONATOMIC 3
#define OBJC_ASSOCIATION_RETAIN 01401
#define OBJC_ASSOCIATION_COPY 01403
'''

FILES["objc/message.h"] = '#pragma once\n#include "runtime.h"\n'

# ── UIKit/UIKit.h ──
# ★ 用 #include 而不是 #import：我们的 stub 是扁平布局，没有 -fmodules 支持
FILES["UIKit/UIKit.h"] = r'''
#pragma once
#include "Foundation/Foundation.h"
#include "CVGeom.h"
#include "objc/runtime.h"

typedef NSInteger UIUserInterfaceStyle;
typedef NSInteger NSLayoutAttribute;
typedef NSInteger NSLayoutRelation;
typedef NSInteger NSTextAlignment;
typedef NSInteger UIViewContentMode;
typedef NSInteger UIControlEvents;
typedef NSInteger UIControlState;
typedef NSInteger UIButtonType;
typedef NSInteger UITextFieldViewMode;
typedef NSInteger UIKeyboardType;
typedef NSInteger UIReturnKeyType;
typedef NSInteger UITextAutocorrectionType;
typedef NSInteger UITextAutocapitalizationType;
typedef NSInteger UITextSpellCheckingType;
typedef NSInteger UIActivityIndicatorViewStyle;
typedef NSInteger UIAlertControllerStyle;
typedef NSInteger UIAlertActionStyle;
typedef NSInteger UIBarButtonItemStyle;
typedef NSInteger UIStatusBarStyle;
typedef NSInteger UIModalPresentationStyle;
typedef NSInteger UISceneActivationState;
typedef NSInteger UIViewAnimationOptions;
typedef NSInteger UIViewKeyframeAnimationOptions;
typedef NSInteger UIFontWeight;
typedef NSInteger UIInterfaceOrientation;
typedef NSInteger UIDeviceOrientation;
typedef NSInteger UIUserInterfaceIdiom;

@class UIView, UIViewController, UIWindow, UIWindowScene, UIScene;
@class UIColor, UIFont, UIImage, UILabel, UIButton, UITextField, UIScrollView;
@class UIImageView, UIActivityIndicatorView, UIAlertController, UIAlertAction;
@class UITapGestureRecognizer, UIGestureRecognizer, UIPanGestureRecognizer;
@class UIScreen, UIDevice, UIApplication, UIPasteboard;
@class NSLayoutConstraint, NSLayoutAnchor, NSLayoutXAxisAnchor, NSLayoutYAxisAnchor;
@class NSLayoutDimension, UILayoutGuide, UIStackView, UITableView, UICollectionView;
@class UINavigationController, UITabBarController, UINavigationBar, UIBarButtonItem;
@class UISlider, UISwitch, UISegmentedControl, UIRefreshControl;
@class CALayer, CAGradientLayer, CAShapeLayer, CAAnimation, CAKeyframeAnimation, CABasicAnimation, CATransaction;
@class UIBezierPath, UIGraphicsImageRenderer, UIGraphicsImageRendererFormat, UIGraphicsImageRendererContext;
@class UIEvent, UITouch, UIMenu, UIAction, UIEditMenuInteraction, UIKeyCommand;
@class NSUUID;

// ── UIResponder ──
@interface UIResponder : NSObject
@property (nonatomic, readonly) BOOL canBecomeFirstResponder;
@property (nonatomic, readonly) BOOL canResignFirstResponder;
- (BOOL)becomeFirstResponder;
- (BOOL)resignFirstResponder;
@property (nonatomic, readonly) UIResponder *nextResponder;
- (void)touchesBegan:(id)t withEvent:(UIEvent *)e;
@end

// ── UIColor ──
@interface UIColor : NSObject
+ (UIColor *)colorWithRed:(CGFloat)r green:(CGFloat)g blue:(CGFloat)b alpha:(CGFloat)a;
+ (UIColor *)colorWithWhite:(CGFloat)w alpha:(CGFloat)a;
+ (UIColor *)colorWithHue:(CGFloat)h saturation:(CGFloat)s brightness:(CGFloat)b alpha:(CGFloat)a;
+ (UIColor *)clearColor;
+ (UIColor *)whiteColor;
+ (UIColor *)blackColor;
+ (UIColor *)grayColor;
+ (UIColor *)lightGrayColor;
+ (UIColor *)darkGrayColor;
+ (UIColor *)redColor;
+ (UIColor *)greenColor;
+ (UIColor *)blueColor;
+ (UIColor *)yellowColor;
+ (UIColor *)orangeColor;
+ (UIColor *)purpleColor;
+ (UIColor *)systemBlueColor;
+ (UIColor *)systemGreenColor;
+ (UIColor *)systemRedColor;
+ (UIColor *)systemOrangeColor;
+ (UIColor *)systemYellowColor;
+ (UIColor *)systemGrayColor;
+ (UIColor *)systemGray6Color;
+ (UIColor *)labelColor;
+ (UIColor *)secondaryLabelColor;
+ (UIColor *)systemBackgroundColor;
+ (UIColor *)secondarySystemBackgroundColor;
- (UIColor *)colorWithAlphaComponent:(CGFloat)a;
@property (nonatomic, readonly) CGFloat red;
@property (nonatomic, readonly) CGFloat green;
@property (nonatomic, readonly) CGFloat blue;
@property (nonatomic, readonly) CGFloat alpha;
- (BOOL)getRed:(CGFloat *)r green:(CGFloat *)g blue:(CGFloat *)b alpha:(CGFloat *)a;
- (CGColorRef)CGColor;
@end

// ── UIFont ──
@interface UIFont : NSObject
+ (UIFont *)systemFontOfSize:(CGFloat)s;
+ (UIFont *)boldSystemFontOfSize:(CGFloat)s;
+ (UIFont *)italicSystemFontOfSize:(CGFloat)s;
+ (UIFont *)systemFontOfSize:(CGFloat)s weight:(CGFloat)w;
+ (UIFont *)monospacedSystemFontOfSize:(CGFloat)s weight:(CGFloat)w;
+ (UIFont *)monospacedDigitSystemFontOfSize:(CGFloat)s weight:(CGFloat)w;
+ (UIFont *)fontWithName:(NSString *)n size:(CGFloat)s;
+ (UIFont *)preferredFontForTextStyle:(NSString *)s;
@property (nonatomic, readonly) CGFloat pointSize;
@property (nonatomic, readonly) NSString *fontName;
@end

// ── UIImage ──
@interface UIImage : NSObject
+ (UIImage *)imageNamed:(NSString *)n;
+ (UIImage *)imageNamed:(NSString *)n inBundle:(NSBundle *)b compatibleWithTraitCollection:(id)t;
+ (UIImage *)imageWithContentsOfFile:(NSString *)p;
+ (UIImage *)imageWithData:(NSData *)d;
+ (UIImage *)imageWithData:(NSData *)d scale:(CGFloat)s;
+ (UIImage *)imageWithCGImage:(void *)img;
- (NSData *)PNGData;
- (NSData *)JPEGDataWithCompressionQuality:(CGFloat)q;
- (UIImage *)imageWithRenderingMode:(NSInteger)m;
@property (nonatomic, readonly) CGSize size;
@property (nonatomic, readonly) CGFloat scale;
@end

// ── UIView ──
@interface UIView : UIResponder
- (instancetype)init;
- (instancetype)initWithFrame:(CGRect)f;
- (instancetype)initWithCoder:(id)c;
@property (nonatomic) CGRect frame;
@property (nonatomic) CGRect bounds;
@property (nonatomic) CGPoint center;
@property (nonatomic) CGPoint origin;
@property (nonatomic) CGSize size;
@property (nonatomic) CGFloat alpha;
@property (nonatomic) BOOL hidden;
@property (nonatomic) BOOL opaque;
@property (nonatomic) BOOL clipsToBounds;
@property (nonatomic) BOOL userInteractionEnabled;
@property (nonatomic) BOOL multipleTouchEnabled;
@property (nonatomic) BOOL exclusiveTouch;
@property (nonatomic) BOOL autoresizesSubviews;
@property (nonatomic, copy) NSString *accessibilityLabel;
@property (nonatomic, copy) NSString *accessibilityIdentifier;
@property (nonatomic) NSInteger tag;
@property (nonatomic, readonly) UIView *superview;
@property (nonatomic, readonly) NSArray *subviews;
@property (nonatomic, readonly) CALayer *layer;
@property (nonatomic) CGAffineTransform transform;
@property (nonatomic, copy) UIColor *tintColor;
@property (nonatomic, copy) UIColor *backgroundColor;
@property (nonatomic) UIViewContentMode contentMode;
@property (nonatomic) BOOL translatesAutoresizingMaskIntoConstraints;
@property (nonatomic) NSInteger autoresizingMask;
@property (nonatomic, readonly) BOOL isFirstResponder;
- (BOOL)isDescendantOfView:(UIView *)v;
@property (nonatomic, readonly) UIView *window;
@property (nonatomic, readonly) UILayoutGuide *safeAreaLayoutGuide;
@property (nonatomic, readonly) BOOL isFocused;
- (void)addSubview:(UIView *)v;
- (void)insertSubview:(UIView *)v atIndex:(NSInteger)i;
- (void)insertSubview:(UIView *)v belowSubview:(UIView *)s;
- (void)insertSubview:(UIView *)v aboveSubview:(UIView *)s;
- (void)bringSubviewToFront:(UIView *)v;
- (void)sendSubviewToBack:(UIView *)v;
- (void)removeFromSuperview;
- (void)layoutIfNeeded;
- (void)setNeedsLayout;
- (void)setNeedsDisplay;
- (void)layoutSubviews;
- (void)didMoveToSuperview;
- (void)willMoveToSuperview:(UIView *)v;
- (void)didMoveToWindow;
- (CGPoint)convertPoint:(CGPoint)p fromView:(UIView *)v;
- (CGPoint)convertPoint:(CGPoint)p toView:(UIView *)v;
- (CGRect)convertRect:(CGRect)r fromView:(UIView *)v;
- (CGRect)convertRect:(CGRect)r toView:(UIView *)v;
- (UIView *)viewWithTag:(NSInteger)t;
- (UIView *)hitTest:(CGPoint)p withEvent:(UIEvent *)e;
- (BOOL)pointInside:(CGPoint)p withEvent:(UIEvent *)e;
- (void)touchesBegan:(id)touches withEvent:(UIEvent *)e;
- (void)touchesMoved:(id)touches withEvent:(UIEvent *)e;
- (void)touchesEnded:(id)touches withEvent:(UIEvent *)e;
- (void)touchesCancelled:(id)touches withEvent:(UIEvent *)e;
- (void)addGestureRecognizer:(UIGestureRecognizer *)g;
- (void)removeGestureRecognizer:(UIGestureRecognizer *)g;
- (void)addConstraint:(NSLayoutConstraint *)c;
- (void)removeConstraint:(NSLayoutConstraint *)c;
- (void)addConstraints:(NSArray *)cs;
- (void)addLayoutGuide:(UILayoutGuide *)g;
- (void)removeLayoutGuide:(UILayoutGuide *)g;
- (void)setContentHuggingPriority:(CGFloat)p forAxis:(NSInteger)a;
- (void)setContentCompressionResistancePriority:(CGFloat)p forAxis:(NSInteger)a;
- (CGSize)systemLayoutSizeFittingSize:(CGSize)s;
- (CGSize)sizeThatFits:(CGSize)s;
+ (void)animateWithDuration:(NSTimeInterval)d animations:(void (^)(void))a;
+ (void)animateWithDuration:(NSTimeInterval)d animations:(void (^)(void))a completion:(void (^)(BOOL f))c;
+ (void)animateWithDuration:(NSTimeInterval)d delay:(NSTimeInterval)dl options:(NSInteger)o animations:(void (^)(void))a completion:(void (^)(BOOL f))c;
+ (void)animateWithDuration:(NSTimeInterval)d
                      delay:(NSTimeInterval)delay
                    options:(NSInteger)o
                 animations:(void (^)(void))a
                 completion:(void (^)(BOOL f))c;
+ (void)animateWithDuration:(NSTimeInterval)d
                      delay:(NSTimeInterval)delay
     usingSpringWithDamping:(CGFloat)damp
      initialSpringVelocity:(CGFloat)vel
                    options:(NSInteger)o
                 animations:(void (^)(void))a
                 completion:(void (^)(BOOL f))c;
+ (void)transitionWithView:(UIView *)v
                  duration:(NSTimeInterval)d
                   options:(NSInteger)o
                animations:(void (^)(void))a
                completion:(void (^)(BOOL f))c;
+ (void)beginAnimations:(NSString *)n context:(void *)ctx;
+ (void)commitAnimations;
+ (void)setAnimationDuration:(NSTimeInterval)d;
- (void)addAnimation:(id)anim forKey:(NSString *)k;
@end

// ── UIControl ──
@interface UIControl : UIView
@property (nonatomic, readonly) NSInteger state;
@property (nonatomic) BOOL enabled;
@property (nonatomic) BOOL selected;
@property (nonatomic) BOOL highlighted;
- (void)addTarget:(id)target action:(SEL)sel forControlEvents:(NSInteger)ev;
- (void)removeTarget:(id)target action:(SEL)sel forControlEvents:(NSInteger)ev;
- (void)sendActionsForControlEvents:(NSInteger)ev;
@end
FOUNDATION_EXPORT const NSInteger UIControlEventTouchUpInside;
FOUNDATION_EXPORT const NSInteger UIControlEventTouchDown;
FOUNDATION_EXPORT const NSInteger UIControlEventValueChanged;
FOUNDATION_EXPORT const NSInteger UIControlEventAllEvents;
FOUNDATION_EXPORT const NSInteger UIControlEventAllTouchEvents;
FOUNDATION_EXPORT const NSInteger UIControlStateNormal;
FOUNDATION_EXPORT const NSInteger UIControlStateHighlighted;
FOUNDATION_EXPORT const NSInteger UIControlStateDisabled;
FOUNDATION_EXPORT const NSInteger UIControlStateSelected;

// ── UILabel ──
@interface UILabel : UIView
@property (nonatomic, copy) NSString *text;
@property (nonatomic, copy) NSAttributedString *attributedText;
@property (nonatomic, copy) UIColor *textColor;
@property (nonatomic, copy) UIFont *font;
@property (nonatomic) NSInteger textAlignment;
@property (nonatomic) NSInteger lineBreakMode;
@property (nonatomic) NSInteger numberOfLines;
@property (nonatomic) BOOL adjustsFontSizeToFitWidth;
@property (nonatomic) CGFloat minimumScaleFactor;
@property (nonatomic) CGFloat preferredMaxLayoutWidth;
@property (nonatomic) BOOL highlighted;
@property (nonatomic, copy) UIColor *highlightedTextColor;
- (CGSize)sizeThatFits:(CGSize)s;
- (void)sizeToFit;
@end

// ── UIImageView ──
@interface UIImageView : UIView
- (instancetype)initWithImage:(UIImage *)i;
@property (nonatomic, strong) UIImage *image;
@property (nonatomic, strong) UIImage *highlightedImage;
@property (nonatomic, copy) NSArray *animationImages;
@property (nonatomic) NSTimeInterval animationDuration;
- (void)startAnimating;
- (void)stopAnimating;
@end

// ── UIButton ──
@interface UIButton : UIControl
+ (instancetype)buttonWithType:(NSInteger)t;
@property (nonatomic, readonly) UILabel *titleLabel;
- (void)setTitle:(NSString *)t forState:(NSInteger)s;
- (NSString *)titleForState:(NSInteger)s;
- (void)setTitleColor:(UIColor *)c forState:(NSInteger)s;
- (UIColor *)titleColorForState:(NSInteger)s;
- (NSString *)currentTitle;
- (NSAttributedString *)currentAttributedTitle;
- (void)setAttributedTitle:(NSAttributedString *)t forState:(NSInteger)s;
- (void)setImage:(UIImage *)i forState:(NSInteger)s;
- (void)setBackgroundImage:(UIImage *)i forState:(NSInteger)s;
- (void)setShowsTouchWhenHighlighted:(BOOL)b;
@property (nonatomic) BOOL showsMenuAsPrimaryAction;
@property (nonatomic) BOOL adjustsImageWhenHighlighted;
@property (nonatomic) UIEdgeInsets contentEdgeInsets;
- (void)enumerateEventHandlers:(void (^)(void *h, UIAction *a, BOOL *stop))b;
@end

// ── UITextField ──
@interface UITextField : UIControl
@property (nonatomic, copy) NSString *text;
@property (nonatomic, copy) NSString *placeholder;
@property (nonatomic, copy) NSAttributedString *attributedPlaceholder;
@property (nonatomic, copy) UIFont *font;
@property (nonatomic, copy) UIColor *textColor;
@property (nonatomic, copy) UIColor *tintColor;
@property (nonatomic) NSInteger textAlignment;
@property (nonatomic) NSInteger borderStyle;
@property (nonatomic) NSInteger clearButtonMode;
@property (nonatomic) BOOL secureTextEntry;
@property (nonatomic) NSInteger keyboardType;
@property (nonatomic) NSInteger returnKeyType;
@property (nonatomic) NSInteger autocorrectionType;
@property (nonatomic) NSInteger autocapitalizationType;
@property (nonatomic) NSInteger spellCheckingType;
@property (nonatomic) NSInteger keyboardAppearance;
@property (nonatomic, weak) id delegate;
@property (nonatomic, copy) UIColor *backgroundColor;
@property (nonatomic) BOOL enablesReturnKeyAutomatically;
- (BOOL)becomeFirstResponder;
- (BOOL)resignFirstResponder;
- (void)addTarget:(id)t action:(SEL)s forControlEvents:(NSInteger)e;
- (void)removeTarget:(id)t action:(SEL)s forControlEvents:(NSInteger)e;
- (UIMenu *)editMenuForCharactersInRange:(NSRange)r suggestedActions:(NSArray *)a;
@end

@protocol UITextFieldDelegate <NSObject>
@optional
- (BOOL)textFieldShouldBeginEditing:(UITextField *)tf;
- (void)textFieldDidBeginEditing:(UITextField *)tf;
- (BOOL)textFieldShouldEndEditing:(UITextField *)tf;
- (void)textFieldDidEndEditing:(UITextField *)tf;
- (void)textFieldDidEndEditing:(UITextField *)tf reason:(NSInteger)r;
- (BOOL)textField:(UITextField *)tf shouldChangeCharactersInRange:(NSRange)r replacementString:(NSString *)s;
- (BOOL)textFieldShouldClear:(UITextField *)tf;
- (BOOL)textFieldShouldReturn:(UITextField *)tf;
- (void)textFieldDidChangeSelection:(UITextField *)tf;
- (UIMenu *)textField:(UITextField *)tf editMenuForCharactersInRange:(NSRange)r suggestedActions:(NSArray *)a;
- (void)textField:(UITextField *)tf willPresentEditMenuWithAnimator:(id)a;
- (void)textField:(UITextField *)tf willDismissEditMenuWithAnimator:(id)a;
@end

// ── UIActivityIndicatorView ──
@interface UIActivityIndicatorView : UIView
- (instancetype)initWithActivityIndicatorStyle:(NSInteger)s;
@property (nonatomic, copy) UIColor *color;
@property (nonatomic) BOOL hidesWhenStopped;
- (void)startAnimating;
- (void)stopAnimating;
@property (nonatomic, readonly) BOOL isAnimating;
@end

// ── UIPasteboard ──
@interface UIPasteboard : NSObject
+ (UIPasteboard *)generalPasteboard;
@property (nonatomic, copy) NSString *string;
@property (nonatomic, copy) NSArray *strings;
@property (nonatomic, copy) UIImage *image;
@property (nonatomic, copy) NSData *data;
@end

// ── UIScreen / UIDevice ──
@interface UIScreen : NSObject
+ (UIScreen *)mainScreen;
@property (nonatomic, readonly) CGRect bounds;
@property (nonatomic, readonly) CGFloat scale;
@property (nonatomic, readonly) CGFloat nativeScale;
@property (nonatomic, readonly) NSArray *screens;
@property (nonatomic, readonly) NSArray *availableModes;
@end

@interface UIDevice (UIKitAdditions)
@property (nonatomic, readonly) NSString *systemName;
@property (nonatomic, readonly) NSInteger userInterfaceIdiom;
@property (nonatomic, readonly) BOOL isMultitaskingSupported;
@property (nonatomic) BOOL batteryMonitoringEnabled;
@end

// ── UIApplication / UIWindow ──
@interface UIApplication : NSObject
+ (UIApplication *)sharedApplication;
@property (nonatomic, readonly) UIWindow *keyWindow;
@property (nonatomic, readonly) NSArray *windows;
@property (nonatomic, readonly) NSArray *connectedScenes;
- (BOOL)openURL:(NSURL *)u;
- (void)openURL:(NSURL *)u options:(NSDictionary *)o completionHandler:(void (^)(BOOL ok))h;
- (BOOL)canOpenURL:(NSURL *)u;
- (void)setStatusBarStyle:(NSInteger)s;
@property (nonatomic) NSInteger applicationIconBadgeNumber;
@property (nonatomic, readonly) NSInteger applicationState;
@property (nonatomic) BOOL idleTimerDisabled;
@end
FOUNDATION_EXPORT const NSInteger UIApplicationStateActive;
FOUNDATION_EXPORT const NSInteger UIApplicationStateBackground;
FOUNDATION_EXPORT const NSInteger UIApplicationStateInactive;

@interface UIScene : NSObject
@property (nonatomic, readonly) NSInteger activationState;
@property (nonatomic, readonly) NSString *title;
@end

@interface UIWindowScene : UIScene
@property (nonatomic, readonly) NSArray *windows;
@property (nonatomic, readonly) UIScreen *screen;
@property (nonatomic, readonly) NSInteger interfaceOrientation;
@property (nonatomic, readonly) BOOL isFullScreen;
@end

@interface UIWindow : UIView
@property (nonatomic, strong) UIViewController *rootViewController;
@property (nonatomic, readonly) BOOL isKeyWindow;
@property (nonatomic, readonly) NSInteger windowLevel;
@property (nonatomic, readonly) UIScene *windowScene;
@property (nonatomic, readonly) UIEdgeInsets safeAreaInsets;
- (void)makeKeyAndVisible;
- (void)makeKeyWindow;
- (void)becomeKeyWindow;
- (void)resignKeyWindow;
@end

// ── UIViewController ──
@interface UIViewController : UIResponder
@property (nonatomic, strong) UIView *view;
@property (nonatomic, readonly) BOOL isViewLoaded;
@property (nonatomic, copy) NSString *title;
@property (nonatomic, readonly) UIViewController *presentedViewController;
@property (nonatomic, readonly) UIViewController *presentingViewController;
@property (nonatomic, readonly) UIViewController *parentViewController;
@property (nonatomic, readonly) NSArray *childViewControllers;
@property (nonatomic, readonly) NSInteger interfaceOrientation;
@property (nonatomic, readonly) UIWindow *window;
@property (nonatomic) UIModalPresentationStyle modalPresentationStyle;
@property (nonatomic) BOOL definesPresentationContext;
- (void)viewDidLoad;
- (void)viewWillAppear:(BOOL)a;
- (void)viewDidAppear:(BOOL)a;
- (void)viewWillDisappear:(BOOL)a;
- (void)viewDidDisappear:(BOOL)a;
- (void)viewWillLayoutSubviews;
- (void)viewDidLayoutSubviews;
- (void)loadView;
- (void)presentViewController:(UIViewController *)vc animated:(BOOL)a completion:(void (^)(void))c;
- (void)dismissViewControllerAnimated:(BOOL)a completion:(void (^)(void))c;
- (void)addChildViewController:(UIViewController *)vc;
- (void)removeFromParentViewController;
- (void)didMoveToParentViewController:(UIViewController *)p;
- (void)willMoveToParentViewController:(UIViewController *)p;
@property (nonatomic) UIEdgeInsets additionalSafeAreaInsets;
@end

// ── UINavigationController ──
@interface UINavigationController : UIViewController
- (instancetype)initWithRootViewController:(UIViewController *)vc;
@property (nonatomic, readonly) NSArray *viewControllers;
- (void)pushViewController:(UIViewController *)vc animated:(BOOL)a;
- (UIViewController *)popViewControllerAnimated:(BOOL)a;
@property (nonatomic, readonly) UINavigationBar *navigationBar;
@end
@interface UINavigationBar : UIView
@end

// ── UIAlertController ──
@interface UIAlertAction : NSObject
+ (instancetype)actionWithTitle:(NSString *)t style:(NSInteger)s handler:(void (^)(UIAlertAction *a))h;
@property (nonatomic) BOOL enabled;
@end

@interface UIAlertController : UIViewController
+ (instancetype)alertControllerWithTitle:(NSString *)t message:(NSString *)m preferredStyle:(NSInteger)s;
- (void)addAction:(UIAlertAction *)a;
- (void)addTextFieldWithConfigurationHandler:(void (^)(UITextField *tf))h;
@property (nonatomic, readonly) NSArray *textFields;
@property (nonatomic, readonly) NSArray *actions;
@end
FOUNDATION_EXPORT const NSInteger UIAlertControllerStyleAlert;
FOUNDATION_EXPORT const NSInteger UIAlertControllerStyleActionSheet;
FOUNDATION_EXPORT const NSInteger UIAlertActionStyleDefault;
FOUNDATION_EXPORT const NSInteger UIAlertActionStyleCancel;
FOUNDATION_EXPORT const NSInteger UIAlertActionStyleDestructive;

// ── 手势 ──
@interface UIGestureRecognizer : NSObject
- (instancetype)initWithTarget:(id)t action:(SEL)a;
@property (nonatomic) BOOL enabled;
@property (nonatomic) BOOL cancelsTouchesInView;
@property (nonatomic) BOOL delaysTouchesBegan;
@property (nonatomic) BOOL delaysTouchesEnded;
@property (nonatomic, readonly) NSInteger state;
@property (nonatomic, readonly) UIView *view;
- (void)requireGestureRecognizerToFail:(UIGestureRecognizer *)g;
- (void)addTarget:(id)t action:(SEL)a;
- (void)removeTarget:(id)t action:(SEL)a;
@end

@interface UITapGestureRecognizer : UIGestureRecognizer
@property (nonatomic) NSInteger numberOfTapsRequired;
@property (nonatomic) NSInteger numberOfTouchesRequired;
@end

// ── 自动布局 ──
@interface NSLayoutConstraint : NSObject
+ (void)activateConstraints:(NSArray *)cs;
+ (void)deactivateConstraints:(NSArray *)cs;
+ (instancetype)constraintWithItem:(id)item
                         attribute:(NSInteger)attr
                         relatedBy:(NSInteger)rel
                            toItem:(id)toItem
                         attribute:(NSInteger)attr2
                        multiplier:(CGFloat)m
                          constant:(CGFloat)c;
@property (nonatomic) CGFloat constant;
@property (nonatomic) CGFloat priority;
@property (nonatomic) BOOL active;
@end

@interface NSLayoutAnchor : NSObject
@end
@interface NSLayoutXAxisAnchor : NSLayoutAnchor
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutXAxisAnchor *)a;
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutXAxisAnchor *)a constant:(CGFloat)c;
- (NSLayoutConstraint *)constraintGreaterThanOrEqualToAnchor:(NSLayoutXAxisAnchor *)a constant:(CGFloat)c;
- (NSLayoutConstraint *)constraintLessThanOrEqualToAnchor:(NSLayoutXAxisAnchor *)a constant:(CGFloat)c;
@end
@interface NSLayoutYAxisAnchor : NSLayoutAnchor
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutYAxisAnchor *)a;
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutYAxisAnchor *)a constant:(CGFloat)c;
- (NSLayoutConstraint *)constraintGreaterThanOrEqualToAnchor:(NSLayoutYAxisAnchor *)a constant:(CGFloat)c;
- (NSLayoutConstraint *)constraintLessThanOrEqualToAnchor:(NSLayoutYAxisAnchor *)a constant:(CGFloat)c;
@end
@interface NSLayoutDimension : NSLayoutAnchor
- (NSLayoutConstraint *)constraintEqualToConstant:(CGFloat)c;
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutDimension *)a;
- (NSLayoutConstraint *)constraintEqualToAnchor:(NSLayoutDimension *)a multiplier:(CGFloat)m constant:(CGFloat)c;
@end
@interface UIView (AnchorConstraints)
- (NSLayoutConstraint *)constraintEqualToAnchor:(id)a constant:(CGFloat)c;
@end

@interface UILayoutGuide : NSObject
@property (nonatomic, readonly) NSLayoutXAxisAnchor *leadingAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *trailingAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *centerXAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *topAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *bottomAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *centerYAnchor;
@property (nonatomic, readonly) NSLayoutDimension *widthAnchor;
@property (nonatomic, readonly) NSLayoutDimension *heightAnchor;
@end

@interface UIView (AutoLayoutAnchors)
@property (nonatomic, readonly) NSLayoutXAxisAnchor *leadingAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *trailingAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *leftAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *rightAnchor;
@property (nonatomic, readonly) NSLayoutXAxisAnchor *centerXAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *topAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *bottomAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *centerYAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *firstBaselineAnchor;
@property (nonatomic, readonly) NSLayoutYAxisAnchor *lastBaselineAnchor;
@property (nonatomic, readonly) NSLayoutDimension *widthAnchor;
@property (nonatomic, readonly) NSLayoutDimension *heightAnchor;
- (NSLayoutConstraint *)constraintEqualToAnchor:(id)a;
@end

// ── QuartzCore ──
@interface CALayer : NSObject
+ (instancetype)layer;
@property (nonatomic) CGRect frame;
@property (nonatomic) CGRect bounds;
@property (nonatomic) CGPoint position;
@property (nonatomic) CGPoint anchorPoint;
@property (nonatomic) CGFloat cornerRadius;
@property (nonatomic) BOOL masksToBounds;
@property (nonatomic) CGFloat borderWidth;
@property (nonatomic) CGColorRef borderColor;
@property (nonatomic) float opacity;
@property (nonatomic) BOOL hidden;
@property (nonatomic) CGColorRef backgroundColor;
@property (nonatomic, readonly) NSArray *sublayers;
@property (nonatomic, readonly) CALayer *superlayer;
@property (nonatomic) CATransform3D transform;
@property (nonatomic) CGFloat zPosition;
@property (nonatomic) BOOL allowsEdgeAntialiasing;
@property (nonatomic, strong) CALayer *mask;
@property (nonatomic) CGFloat shadowOpacity;
@property (nonatomic) CGSize shadowOffset;
@property (nonatomic) CGFloat shadowRadius;
@property (nonatomic) CGColorRef shadowColor;
- (void)addSublayer:(CALayer *)l;
- (void)insertSublayer:(CALayer *)l atIndex:(unsigned)i;
- (void)insertSublayer:(CALayer *)l below:(CALayer *)s;
- (void)insertSublayer:(CALayer *)l above:(CALayer *)s;
- (void)removeFromSuperlayer;
- (void)addAnimation:(id)a forKey:(NSString *)k;
- (void)removeAnimationForKey:(NSString *)k;
- (void)removeAllAnimations;
- (id)presentationLayer;
- (id)modelLayer;
- (void)setNeedsLayout;
- (void)layoutIfNeeded;
- (void)setNeedsDisplay;
- (void)display;
@end

@interface CAGradientLayer : CALayer
@property (nonatomic, copy) NSArray *colors;
@property (nonatomic, copy) NSArray *locations;
@property (nonatomic) CGPoint startPoint;
@property (nonatomic) CGPoint endPoint;
@property (nonatomic, copy) NSString *type;
@end

@interface CAShapeLayer : CALayer
@property (nonatomic) void *path;
@property (nonatomic) CGColorRef fillColor;
@property (nonatomic) CGColorRef strokeColor;
@property (nonatomic) CGFloat lineWidth;
@property (nonatomic, copy) NSString *fillRule;
@property (nonatomic) CGFloat strokeStart;
@property (nonatomic) CGFloat strokeEnd;
@property (nonatomic, copy) NSArray *lineDashPattern;
@property (nonatomic) CGFloat lineDashPhase;
@property (nonatomic) CGFloat miterLimit;
@end
FOUNDATION_EXPORT NSString * const kCAFillRuleEvenOdd;
FOUNDATION_EXPORT NSString * const kCAFillRuleNonZero;
FOUNDATION_EXPORT NSString * const kCAGradientLayerAxial;

@interface CAAnimation : NSObject
@property (nonatomic) NSTimeInterval duration;
@property (nonatomic, strong) id delegate;
@property (nonatomic) BOOL removedOnCompletion;
@property (nonatomic, strong) id timingFunction;
@end

@interface CAKeyframeAnimation : CAAnimation
+ (instancetype)animationWithKeyPath:(NSString *)p;
@property (nonatomic, copy) NSArray *values;
@property (nonatomic, copy) NSArray *keyTimes;
@property (nonatomic, copy) NSString *calculationMode;
@property (nonatomic, copy) NSArray *timingFunctions;
@end

@interface CABasicAnimation : CAAnimation
+ (instancetype)animationWithKeyPath:(NSString *)p;
@property (nonatomic, strong) id fromValue;
@property (nonatomic, strong) id toValue;
@property (nonatomic, strong) id byValue;
@end

@interface CATransaction : NSObject
+ (void)begin;
+ (void)commit;
+ (void)setDisableActions:(BOOL)b;
+ (void)setAnimationDuration:(NSTimeInterval)d;
@end

// ── UIBezierPath ──
@interface UIBezierPath : NSObject
+ (instancetype)bezierPathWithRoundedRect:(CGRect)r cornerRadius:(CGFloat)cr;
+ (instancetype)bezierPathWithRoundedRect:(CGRect)r
                             byRoundingCorners:(NSInteger)c
                                   cornerRadii:(CGSize)s;
+ (instancetype)bezierPathWithOvalInRect:(CGRect)r;
+ (instancetype)bezierPathWithRect:(CGRect)r;
+ (instancetype)bezierPath;
- (void)appendPath:(UIBezierPath *)p;
- (void)moveToPoint:(CGPoint)p;
- (void)addLineToPoint:(CGPoint)p;
- (void)addArcWithCenter:(CGPoint)c radius:(CGFloat)r startAngle:(CGFloat)a endAngle:(CGFloat)b clockwise:(BOOL)cw;
- (void)closePath;
- (void)fill;
- (void)stroke;
- (void)addClip;
@property (nonatomic) BOOL usesEvenOddFillRule;
- (CGPathRef)CGPath;
@end

// ── 绘图 ──
@interface UIGraphicsImageRendererFormat : NSObject
+ (instancetype)defaultFormat;
@property (nonatomic) CGFloat scale;
@property (nonatomic) BOOL opaque;
@end

@interface UIGraphicsImageRenderer : NSObject
- (instancetype)initWithSize:(CGSize)s;
- (instancetype)initWithSize:(CGSize)s format:(UIGraphicsImageRendererFormat *)f;
- (UIImage *)imageWithActions:(void (^)(UIGraphicsImageRendererContext *ctx))a;
@end

@interface UIGraphicsImageRendererContext : NSObject
@property (nonatomic, readonly) void *CGContext;
@end

FOUNDATION_EXPORT NSInteger UIDeviceOrientationIsPortrait(NSInteger o);
FOUNDATION_EXPORT const NSInteger UIInterfaceOrientationPortrait;
FOUNDATION_EXPORT const NSInteger UIInterfaceOrientationLandscapeLeft;
FOUNDATION_EXPORT const NSInteger UIInterfaceOrientationLandscapeRight;
FOUNDATION_EXPORT const NSInteger UIInterfaceOrientationPortraitUpsideDown;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingNone;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleWidth;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleHeight;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleLeftMargin;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleRightMargin;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleTopMargin;
FOUNDATION_EXPORT const NSInteger UIViewAutoresizingFlexibleBottomMargin;
FOUNDATION_EXPORT const NSInteger NSTextAlignmentLeft;
FOUNDATION_EXPORT const NSInteger NSTextAlignmentCenter;
FOUNDATION_EXPORT const NSInteger NSTextAlignmentRight;
FOUNDATION_EXPORT const NSInteger NSTextAlignmentNatural;
FOUNDATION_EXPORT const NSInteger UIFontWeightRegular;
FOUNDATION_EXPORT const NSInteger UIFontWeightMedium;
FOUNDATION_EXPORT const NSInteger UIFontWeightSemibold;
FOUNDATION_EXPORT const NSInteger UIFontWeightBold;
FOUNDATION_EXPORT const NSInteger UIFontWeightHeavy;
FOUNDATION_EXPORT const NSInteger UIButtonTypeSystem;
FOUNDATION_EXPORT const NSInteger UIButtonTypeCustom;
FOUNDATION_EXPORT const NSInteger UIButtonTypeRoundedRect;
FOUNDATION_EXPORT const NSInteger UITextFieldViewModeWhileEditing;
FOUNDATION_EXPORT const NSInteger UITextFieldViewModeAlways;
FOUNDATION_EXPORT const NSInteger UITextFieldViewModeNever;
FOUNDATION_EXPORT const NSInteger UIKeyboardTypeDefault;
FOUNDATION_EXPORT const NSInteger UIKeyboardTypeASCIICapable;
FOUNDATION_EXPORT const NSInteger UIKeyboardTypeNumbersAndPunctuation;
FOUNDATION_EXPORT const NSInteger UIReturnKeyDefault;
FOUNDATION_EXPORT const NSInteger UIReturnKeyGo;
FOUNDATION_EXPORT const NSInteger UIReturnKeyDone;
FOUNDATION_EXPORT const NSInteger UITextAutocorrectionTypeNo;
FOUNDATION_EXPORT const NSInteger UITextAutocorrectionTypeDefault;
FOUNDATION_EXPORT const NSInteger UITextAutocapitalizationTypeNone;
FOUNDATION_EXPORT const NSInteger UITextSpellCheckingTypeNo;
FOUNDATION_EXPORT const NSInteger UIActivityIndicatorViewStyleMedium;
FOUNDATION_EXPORT const NSInteger UIActivityIndicatorViewStyleLarge;
FOUNDATION_EXPORT const NSInteger UIViewAnimationOptionCurveEaseOut;
FOUNDATION_EXPORT const NSInteger UIViewAnimationOptionCurveEaseInOut;
FOUNDATION_EXPORT const NSInteger UIViewAnimationOptionAllowUserInteraction;
FOUNDATION_EXPORT const NSInteger UIViewAnimationOptionBeginFromCurrentState;
FOUNDATION_EXPORT const NSInteger UIModalPresentationFullScreen;
FOUNDATION_EXPORT const NSInteger UIModalPresentationOverFullScreen;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeLeft;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeRight;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeTop;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeBottom;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeWidth;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeHeight;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeCenterX;
FOUNDATION_EXPORT const NSInteger NSLayoutAttributeCenterY;
FOUNDATION_EXPORT const NSInteger NSLayoutRelationEqual;
FOUNDATION_EXPORT const NSInteger UIUserInterfaceIdiomPhone;
FOUNDATION_EXPORT const NSInteger UIUserInterfaceIdiomPad;
FOUNDATION_EXPORT NSString * const UIKeyboardWillChangeFrameNotification;
FOUNDATION_EXPORT NSString * const UIKeyboardWillShowNotification;
FOUNDATION_EXPORT NSString * const UIKeyboardWillHideNotification;
FOUNDATION_EXPORT NSString * const UIKeyboardFrameEndUserInfoKey;
FOUNDATION_EXPORT NSString * const UIKeyboardFrameBeginUserInfoKey;
FOUNDATION_EXPORT NSString * const UIKeyboardAnimationDurationUserInfoKey;
FOUNDATION_EXPORT NSString * const UIKeyboardAnimationCurveUserInfoKey;
FOUNDATION_EXPORT NSString * const UIApplicationDidFinishLaunchingNotification;
FOUNDATION_EXPORT NSString * const UIApplicationDidBecomeActiveNotification;
FOUNDATION_EXPORT NSString * const UIApplicationWillResignActiveNotification;
FOUNDATION_EXPORT NSString * const UIApplicationDidEnterBackgroundNotification;
FOUNDATION_EXPORT NSString * const UIApplicationWillEnterForegroundNotification;
FOUNDATION_EXPORT NSString * const UIApplicationWillTerminateNotification;
FOUNDATION_EXPORT NSString * const UIApplicationLaunchOptionsKey;
FOUNDATION_EXPORT NSString * const UIApplicationOpenSettingsURLString;

@interface UIResponder (UIApplicationDelegate)
@end

@protocol UIApplicationDelegate <NSObject>
@optional
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)o;
- (void)applicationDidBecomeActive:(UIApplication *)app;
- (void)applicationWillResignActive:(UIApplication *)app;
- (void)applicationDidEnterBackground:(UIApplication *)app;
- (void)applicationWillEnterForeground:(UIApplication *)app;
- (void)applicationWillTerminate:(UIApplication *)app;
- (BOOL)application:(UIApplication *)app openURL:(NSURL *)u options:(NSDictionary *)o;
@end

FOUNDATION_EXPORT int UIApplicationMain(int argc, char *argv[], NSString *principalClassName, NSString *delegateClassName);
'''

# ── Security ──
FILES["Security/Security.h"] = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
typedef unsigned char UInt8;
typedef signed char SInt8;
typedef unsigned int UInt32;
typedef signed int SInt32;
typedef long SInt64;
typedef unsigned long UInt64;
typedef double Float64;
typedef int Boolean;
#define CFTypeRef const void *
typedef struct __SecKey *SecKeyRef;
typedef struct __SecCertificate *SecCertificateRef;
typedef struct __SecPolicy *SecPolicyRef;
typedef struct __SecTrust *SecTrustRef;
typedef struct __CFData *CFDataRef;
typedef struct __CFDictionary *CFDictionaryRef;
typedef struct __CFString *CFStringRef;
typedef struct __CFError *CFErrorRef;
typedef struct __CFAllocator *CFAllocatorRef;

typedef unsigned int SecPadding;
typedef unsigned int SecKeyAlgorithm;
typedef long OSStatus;
typedef unsigned int CFOptionFlags;

FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSAEncryptionRaw;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSAEncryptionPKCS1;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSAEncryptionOAEPSHA1;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSAEncryptionOAEPSHA256;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSASignatureDigestPKCS1v15SHA1;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSASignatureDigestPKCS1v15SHA256;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA1;
FOUNDATION_EXPORT const SecKeyAlgorithm kSecKeyAlgorithmRSASignatureMessagePKCS1v15SHA256;
FOUNDATION_EXPORT const SecPadding kSecPaddingNone;
FOUNDATION_EXPORT const SecPadding kSecPaddingPKCS1;
FOUNDATION_EXPORT const SecPadding kSecPaddingOAEP;
FOUNDATION_EXPORT const SecPadding kSecPaddingPKCS1SHA256;
FOUNDATION_EXPORT const SecPadding kSecPaddingPKCS1SHA1;
FOUNDATION_EXPORT const OSStatus errSecSuccess;
FOUNDATION_EXPORT const OSStatus errSecItemNotFound;
FOUNDATION_EXPORT const OSStatus errSecDuplicateItem;
FOUNDATION_EXPORT const OSStatus errSecAuthFailed;
FOUNDATION_EXPORT const OSStatus errSecParam;

FOUNDATION_EXPORT const void *kSecClass;
FOUNDATION_EXPORT const void *kSecClassGenericPassword;
FOUNDATION_EXPORT const void *kSecAttrService;
FOUNDATION_EXPORT const void *kSecAttrAccount;
FOUNDATION_EXPORT const void *kSecValueData;
FOUNDATION_EXPORT const void *kSecReturnData;
FOUNDATION_EXPORT const void *kSecMatchLimit;
FOUNDATION_EXPORT const void *kSecMatchLimitOne;
FOUNDATION_EXPORT const void *kSecAttrAccessible;
FOUNDATION_EXPORT const void *kSecAttrAccessibleAfterFirstUnlock;
FOUNDATION_EXPORT const void *kSecAttrAccessibleWhenUnlocked;
FOUNDATION_EXPORT const void *kSecAttrAccessibleWhenUnlockedThisDeviceOnly;

FOUNDATION_EXPORT OSStatus SecItemAdd(CFDictionaryRef attrs, CFTypeRef *result);
FOUNDATION_EXPORT OSStatus SecItemCopyMatching(CFDictionaryRef query, CFTypeRef *result);
FOUNDATION_EXPORT OSStatus SecItemUpdate(CFDictionaryRef query, CFDictionaryRef attrs);
FOUNDATION_EXPORT OSStatus SecItemDelete(CFDictionaryRef query);

FOUNDATION_EXPORT SecKeyRef SecKeyCreateWithData(CFDataRef keyData,
                                                 CFDictionaryRef attributes,
                                                 CFErrorRef *error);
FOUNDATION_EXPORT void *SecKeyCreateDecryptedData(SecKeyRef key,
                                                    SecKeyAlgorithm alg,
                                                    CFDataRef ciphertext,
                                                    CFErrorRef *error);
FOUNDATION_EXPORT void *SecKeyCreateEncryptedData(SecKeyRef key,
                                                    SecKeyAlgorithm alg,
                                                    CFDataRef plaintext,
                                                    CFErrorRef *error);
FOUNDATION_EXPORT size_t SecKeyGetBlockSize(SecKeyRef key);
FOUNDATION_EXPORT void *SecKeyCreateRandomKey(CFDictionaryRef attrs, CFErrorRef *error);
FOUNDATION_EXPORT void *SecKeyCopyPublicKey(SecKeyRef priv);
FOUNDATION_EXPORT SecKeyRef SecKeyCreateWithData_(void);
FOUNDATION_EXPORT void CFRelease(const void *cf);
FOUNDATION_EXPORT const void *CFRetain(const void *cf);
FOUNDATION_EXPORT void *CFDataCreate(CFAllocatorRef a, const UInt8 *bytes, long len);
FOUNDATION_EXPORT UInt8 *CFDataGetBytePtr(CFDataRef d);
FOUNDATION_EXPORT long CFDataGetLength(CFDataRef d);
FOUNDATION_EXPORT void *CFDictionaryCreate(CFAllocatorRef a,
        const void **keys, const void **values, long numValues,
        const void *keyCallbacks, const void *valueCallbacks);
FOUNDATION_EXPORT void *CFErrorCopyDescription(CFErrorRef e);
FOUNDATION_EXPORT const void *kSecAttrKeyType;
FOUNDATION_EXPORT const void *kSecAttrKeyClass;
FOUNDATION_EXPORT const void *kSecAttrKeySizeInBits;
FOUNDATION_EXPORT const void *kSecAttrKeyTypeRSA;
FOUNDATION_EXPORT const void *kSecAttrKeyClassPublic;
FOUNDATION_EXPORT const void *kSecAttrKeyClassPrivate;
FOUNDATION_EXPORT const void *kSecUseDataProtectionKeychain;
FOUNDATION_EXPORT void *kCFBooleanTrue;
FOUNDATION_EXPORT void *kCFBooleanFalse;
FOUNDATION_EXPORT void *kCFAllocatorDefault;
'''

# ── dispatch（GCD）──
FILES["dispatch/dispatch.h"] = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>

typedef struct dispatch_queue_s *dispatch_queue_t;
typedef struct dispatch_queue_attr_s *dispatch_queue_attr_t;
typedef struct dispatch_group_s *dispatch_group_t;
typedef struct dispatch_semaphore_s *dispatch_semaphore_t;
typedef struct dispatch_source_s *dispatch_source_t;
typedef struct dispatch_time_s { uint64_t v; } dispatch_time_t;
typedef long dispatch_once_t;
typedef void (^dispatch_block_t)(void);

#define DISPATCH_QUEUE_SERIAL     ((dispatch_queue_attr_t)0)
#define DISPATCH_QUEUE_CONCURRENT ((dispatch_queue_attr_t)1)
#define NSEC_PER_SEC 1000000000ull
#define NSEC_PER_MSEC 1000000ull
#define NSEC_PER_USEC 1000ull
#define USEC_PER_SEC 1000000ull
#define DISPATCH_TIME_NOW  ((dispatch_time_t){0})
#define DISPATCH_TIME_FOREVER ((dispatch_time_t){~0ULL})
#define DISPATCH_QUEUE_PRIORITY_HIGH 2
#define DISPATCH_QUEUE_PRIORITY_DEFAULT 0
#define DISPATCH_QUEUE_PRIORITY_LOW (-2)
#define DISPATCH_QUEUE_PRIORITY_BACKGROUND ((intptr_t)0x0800)

extern dispatch_queue_t dispatch_get_main_queue(void);
extern dispatch_queue_t dispatch_get_global_queue(long identifier, unsigned long flags);
extern dispatch_queue_t dispatch_queue_create(const char *label, dispatch_queue_attr_t attr);
extern void dispatch_async(dispatch_queue_t q, dispatch_block_t block);
extern void dispatch_sync(dispatch_queue_t q, dispatch_block_t block);
extern void dispatch_async_f(dispatch_queue_t q, void *ctx, void (*fn)(void *));
extern void dispatch_sync_f(dispatch_queue_t q, void *ctx, void (*fn)(void *));
extern void dispatch_once(dispatch_once_t *predicate, dispatch_block_t block);
extern void dispatch_after(dispatch_time_t when, dispatch_queue_t q, dispatch_block_t block);
extern dispatch_time_t dispatch_time(dispatch_time_t base, int64_t delta);
extern dispatch_time_t dispatch_walltime(const void *base, int64_t delta);
extern void dispatch_main(void);
extern void dispatch_barrier_async(dispatch_queue_t q, dispatch_block_t block);
extern void dispatch_barrier_sync(dispatch_queue_t q, dispatch_block_t block);

extern dispatch_group_t dispatch_group_create(void);
extern void dispatch_group_enter(dispatch_group_t g);
extern void dispatch_group_leave(dispatch_group_t g);
extern void dispatch_group_async(dispatch_group_t g, dispatch_queue_t q, dispatch_block_t block);
extern long dispatch_group_wait(dispatch_group_t g, dispatch_time_t timeout);
extern void dispatch_group_notify(dispatch_group_t g, dispatch_queue_t q, dispatch_block_t block);

extern dispatch_semaphore_t dispatch_semaphore_create(long value);
extern long dispatch_semaphore_wait(dispatch_semaphore_t dsema, dispatch_time_t timeout);
extern long dispatch_semaphore_signal(dispatch_semaphore_t dsema);
'''

FILES["dispatch/dispatch.h"] += "\n"
# ── CommonCrypto ──
FILES["CommonCrypto/CommonDigest.h"] = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
#define CC_MD5_DIGEST_LENGTH 16
typedef uint32_t CC_LONG;
#define CC_SHA1_DIGEST_LENGTH 20
#define CC_SHA256_DIGEST_LENGTH 32
#define CC_SHA512_DIGEST_LENGTH 64
#define CC_MD5_LENGTH 16
#define CC_SHA1_LENGTH 20
#define CC_SHA256_LENGTH 32
#define CC_SHA512_LENGTH 64
typedef struct { uint32_t state[4]; uint64_t count; unsigned char buffer[64]; } CC_MD5_CTX;
typedef struct { uint32_t state[5]; uint64_t count; unsigned char buffer[64]; } CC_SHA1_CTX;
typedef struct { uint32_t state[8]; uint64_t count; unsigned char buffer[64]; } CC_SHA256_CTX;
typedef struct { uint64_t state[8]; uint64_t count; unsigned char buffer[128]; } CC_SHA512_CTX;
extern unsigned char *CC_MD5(const void *data, uint32_t len, unsigned char *md);
extern unsigned char *CC_SHA1(const void *data, uint32_t len, unsigned char *md);
extern unsigned char *CC_SHA256(const void *data, uint32_t len, unsigned char *md);
extern unsigned char *CC_SHA512(const void *data, uint32_t len, unsigned char *md);
extern int CC_MD5_Init(CC_MD5_CTX *c);
extern int CC_MD5_Update(CC_MD5_CTX *c, const void *data, uint32_t len);
extern int CC_MD5_Final(unsigned char *md, CC_MD5_CTX *c);
extern int CC_SHA1_Init(CC_SHA1_CTX *c);
extern int CC_SHA1_Update(CC_SHA1_CTX *c, const void *data, uint32_t len);
extern int CC_SHA1_Final(unsigned char *md, CC_SHA1_CTX *c);
extern int CC_SHA256_Init(CC_SHA256_CTX *c);
extern int CC_SHA256_Update(CC_SHA256_CTX *c, const void *data, uint32_t len);
extern int CC_SHA256_Final(unsigned char *md, CC_SHA256_CTX *c);
extern int CC_SHA512_Init(CC_SHA512_CTX *c);
extern int CC_SHA512_Update(CC_SHA512_CTX *c, const void *data, uint32_t len);
extern int CC_SHA512_Final(unsigned char *md, CC_SHA512_CTX *c);
'''

FILES["CommonCrypto/CommonCryptor.h"] = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
#define kCCEncrypt 0
#define kCCDecrypt 1
#define kCCAlgorithmAES 0
#define kCCOptionPKCS7Padding 0x0001
#define kCCOptionECBMode 0x0002
typedef uint32_t CCCryptorStatus;
typedef uint32_t CCOperation;
typedef uint32_t CCAlgorithm;
typedef uint32_t CCOptions;
typedef struct _CCCryptor *CCCryptorRef;
CCCryptorStatus CCCrypt(CCOperation op, CCAlgorithm alg, CCOptions options,
                        const void *key, size_t keyLength,
                        const void *iv,
                        const void *dataIn, size_t dataInLength,
                        void *dataOut, size_t dataOutAvailable, size_t *dataOutMoved);
'''

FILES["CommonCrypto/CommonHMAC.h"] = r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
typedef uint32_t CCHmacAlgorithm;
#define kCCHmacAlgSHA1 0
#define kCCHmacAlgMD5 1
#define kCCHmacAlgSHA256 2
#define kCCHmacAlgSHA512 3
typedef struct { uint8_t ctx[512]; } CCHmacContext;
extern void CCHmac(CCHmacAlgorithm algorithm, const void *key, size_t keyLength,
                   const void *data, size_t dataLength, void *macOut);
extern void CCHmacInit(CCHmacContext *ctx, CCHmacAlgorithm algorithm,
                       const void *key, size_t keyLength);
extern void CCHmacUpdate(CCHmacContext *ctx, const void *data, size_t dataLength);
extern void CCHmacFinal(CCHmacContext *ctx, void *macOut);
'''

FILES["CommonCrypto/CommonCrypto.h"] = r'''
#pragma once
#include "CommonDigest.h"
#include "CommonCryptor.h"
#include "CommonHMAC.h"
'''

# ── 顶层 UIKit.h / Foundation.h 快捷入口 ──
FILES["UIKit.h"] = '#pragma once\n#import "UIKit/UIKit.h"\n'
FILES["Foundation.h"] = '#pragma once\n#import "Foundation/Foundation.h"\n'


def write_all():
    n = 0
    for rel, content in FILES.items():
        p = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        n += 1
    return n


if __name__ == "__main__":
    cnt = write_all()
    print("已生成 %d 个 stub 头到 %s" % (cnt, ROOT))
