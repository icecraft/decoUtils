#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import traceback
from functools import wraps
import linecache
import time
import math
import logging
import inspect
import cProfile
from threading import Lock
import copy
from .utils import backtrace_f, memorized_args_key, lineDumpFunc
from IPython import embed
import __builtin__


__all__ = ['immutableattr', 'safe_run', 'safe_run_dump', 'trace',
           'dump_args', 'dump_res', 'fronzen_args', 'delayRetry', 'invokerLog',
           'methodWrap', 'trace_when_error', 'trace_when_error_gen',
           'test_run', 'timecal', 'profileit', 'lineDump',
           'exceptionDump', 'btDump',
           'memorized', 'memorized_timeout', 'invoking_warning']


def profileit(func):
    def wrapper(*args, **kwargs):
        datafn = func.__name__ + ".profile"  # Name the data file sensibly
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        prof.dump_stats(datafn)
        return retval
    return wrapper


# 重试若干次，如果还是失败。则直接 return 0，让 rq 清理这个任务
# todo: 如果那样还是失败，则 log 出来
# Attention: 暂时用不了，因为不知道如何将一个失败的任务塞到 rq 队列中。以及如何将错误日志 log 出来
def redis_retry(tries=3):
    def _redis_retry(func):
        try_times = [tries]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if try_times[-1] > 0:
                try_times[-1] -= 1
                return func(*args, **kwargs)
            else:
                return 0
        return wrapper
    return _redis_retry


def synchronized(lock):
    '''Synchronization decorator. copy from
https://wiki.python.org/moin/PythonDecoratorLibrary'''
    
    def wrap(f):
        @wraps(f)
        def new_function(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return new_function
    return wrap


def simpleJobQueue(func):
    # 调用该函数的函数将不会获得有效的返回值
    # 等于将这个函数转化成一个简陋的 job Queue，
    # 每次调用这个函数都是往工作队列中塞任务，且运行任务队列中已有的任务
    queue = [[]]
    queueAccessLock = Lock()
    workLock = Lock()
    
    @synchronized(queueAccessLock)
    def _get_queue_data():
        data, queue[-1] = queue[-1], []
        return data
    
    @synchronized(queueAccessLock)
    def _update_queue_data(*args, **kwargs):
        queue[-1].append((args, kwargs))  # 有问题
        return

    @synchronized(queueAccessLock)
    def _pop_queue():
        return queue[-1].pop()

    def _iter_queue_data():
        while 1:
            try:
                yield _pop_queue()
            except IndexError:
                raise StopIteration
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        _update_queue_data(*args, **kwargs)
        if workLock.acquire(False) is False:
            return
        try:  # if 语句中已经获取锁，所以要在 finally 中释放
            for jobargs in _iter_queue_data():
                func(*jobargs[0], **jobargs[1])
        finally:
            workLock.release()
    return wrapper


"""
def fib(n, _memo={0:1, 1:1}):
    if n in _memo:
        return _memo[n]
    else:
        _memo[n] = fib(n-1) + fib(n-2)
        return _memo[n]
以上的写法也可以达到 memorized 效果, function object 还是有些不了解的
"""


"""
def fib(n):
    if n in fib.cache:
        print "found fib.cache[%d] = %d: " %(n, fib.cache[n])
        return fib.cache[n]
    else:
        print "fib.cache[%d] = fib(%d) + fib(%d)" % (n, n-1, n-2)
        fib.cache[n] = fib(n-1) + fib(n-2)
        print "modified fib.cache: ", fib.cache
        return fib.cache[n]

fib.cache = {0:0, 1:1}  # 用 fib.func_dict  存储数值
# it is not cute
"""


def memorized(func):
    save_res = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        tuple_name = memorized_args_key(func, *args, **kwargs)
        if tuple_name in save_res:
            return save_res[tuple_name]
        else:
            save_res[tuple_name] = value = func(*args, **kwargs)
            return value
    return wrapper


def memorized_timeout(timeout):
    def memorized(func):
        save_res = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            tuple_name = memorized_args_key(func, *args, **kwargs)
            if tuple_name in save_res and save_res[tuple_name]['timeout'] > time.time():
                return save_res[tuple_name]['res']
            else:
                res = {}
                res['res'] = value = func(*args, **kwargs)
                res['timeout'] = time.time() + timeout
                save_res[tuple_name] = res
                return value
        return wrapper
    return memorized


def timecal(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        time_start = time.clock()
        res = func(*args, **kwargs)
        time_end = time.clock()
        print 'time cost : %s' % repr(time_end - time_start)
        return res
    return wrapper


def test_run(*targs):
    '''[expect, arg1, arg2], [expect, arg1, arg2] '''
    def _test_run(func):
        @wraps(func)
        def wrapper():
            for args in targs:
                if args[0] == func(args[1], args[2]):
                    print 'True for %s' % repr(args)
                else:
                    print 'False for %s' % repr(args)
        return wrapper()
    return _test_run

        
def immutableattr(func):
        cache = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if len(cache) == 0:
                cache.append(func(*args, **kwargs))
                return cache[-1]
        return wrapper
                                        
    
def safe_run(func):
    # seems can not be used with generator
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return None
    return wrapper


def safe_run_dump(func):
    # can not be used with generator
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            ex_type, ex, tb = sys.exc_info()
            traceback.print_tb(tb)
            backtrace_f(sys._getframe())
            return None
    return wrapper


def trace_when_error(func):
    """ copy this function from  
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return _dump
        return None
    
    def _dump(frame, why, arg):
        if why == "exception":
            # record the file name and line number of every trace
            import pdb
            pdb.set_trace()
                
        return _dump

    @wraps(func)
    def wrapper(*args, **kwargs):
        save_trace.append(sys.gettrace())
        sys.settrace(globaltrace)
        try:
            return func(*args, **kwargs)
        finally:
            sys.settrace(save_trace[-1])

    return wrapper


def trace_when_error_gen(func):
    """ copy this function from  
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return _dump
        return None
    
    def _dump(frame, why, arg):
        if why == "exception":
            # record the file name and line number of every trace
            import pdb
            pdb.set_trace()
        return _dump

    @wraps(func)
    def wrapper(*args, **kwargs):
        save_trace.append(sys.gettrace())
        sys.settrace(globaltrace)
        try:
            for i in func(*args, **kwargs):
                yield i
        finally:
            sys.settrace(save_trace[-1])

    return wrapper


def trace(func):
    save_trace = []
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            save_trace.append(sys.gettrace())
            import pdb
            pdb.set_trace()
            return func(*args, **kwargs)
        finally:
            sys.settrace(save_trace[-1])
    return wrapper


def btDump(procFrameFunc=lineDumpFunc(), verbose=False):
    def _detail_dump(f):
        while f:
            if verbose:
                procFrameFunc(f)
            else:
                print f.f_code
            f = f.f_back
        
    def decorated_func(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            f = sys._getframe()
            _detail_dump(f)
            return func(*args, **kwargs)
        return wrapper
    return decorated_func


def lineDump(procFrameFunc=lineDumpFunc()):
    """ copy this function from
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    func_obj = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return _dump
        return None

    def _in_wrapfunc(frame, func):
        return id(frame.f_code.co_code) == id(func.func_code.co_code)
    
    def _dump(frame, why, arg):
        if why == "line" and _in_wrapfunc(frame, func_obj[0]):
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            bname = os.path.basename(filename)
            
            print "{}({}): {}".format(bname,
                                      lineno,
                                      linecache.getline(filename, lineno))
            procFrameFunc(frame)
        return _dump
    
    def wrapper(f):
        func_obj.append(f)
        
        @wraps(f)
        def _f(*args, **kwds):
            save_trace.append(sys.gettrace())
            sys.settrace(globaltrace)
            try:
                return f(*args, **kwds)
            finally:
                sys.settrace(save_trace[-1])
        return _f
    return wrapper


def exceptionDump(procFrameFunc=lineDumpFunc()):
    """ copy this function from  
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return _dump
        return None
    
    def _dump(frame, why, arg):
        if why == "exception":
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            bname = os.path.basename(filename)
            
            print "{}({}): {}".format(bname,
                                      lineno,
                                      linecache.getline(filename, lineno))
            procFrameFunc(frame)
        return _dump
    
    def wrapper(f):
        @wraps(f)
        def _f(*args, **kwargs):
            save_trace.append(sys.gettrace())
            sys.settrace(globaltrace)
            try:
                return f(*args, **kwargs)
            finally:
                sys.settrace(save_trace[-1])
        return _f
    return wrapper


def dump_args(func):
    """This decorator dumps out the arguments passed to
a function before calling it and this code was copy from
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
"""
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        print args, kwargs
        print fname, ":", ', '.join(
            '%s=%r' % entry
            for entry in zip(argnames, args) +
            [('*args', list(args[func.func_code.co_argcount:]))] +
            kwargs.items())
        
        return func(*args, **kwargs)

    return wrapper


def dump_res(func):
    # 打印出函数的运行结果
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        print func.func_name, ":", "result is :", res
        return res
    return wrapper


# Retry decorator with exponential backoff and defaultValue
def delayRetry(tries, delay=3, backoff=2, defaultValue=None):
    '''Retries a function or method until it returns True.
    delay sets the initial delay in seconds, and backoff sets the factor by which
    the delay should lengthen after each failure. backoff must be greater than 1,
    or else it isn't really a backoff. tries must be at least 0, and delay
    greater than 0.'''

    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            while mtries > 0:
                try:
                    return f(*args, **kwargs)   # Try again
                except:
                    mtries -= 1          # consume an attempt
                    time.sleep(mdelay)   # wait...
                    mdelay *= backoff    # make future wait longer

            return defaultValue   # Ran out of tries :-(

        return f_retry   # true decorator -> decorated function
    return deco_retry


def invokerLog(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        logging.error('now enter')
        res = func(*args, **kwargs)
        logging.error('now exit')
        return res
    return wrap


class CustomAttr:
    def __init__(self, obj, wrapFunc=invokerLog):
        self.attr = "a custom function attribute"
        self.obj = obj
        self.wrapFunc = wrapFunc
        self._instance = None
        
    def __call__(self, *args, **kwargs):
        self._instance = self.obj(*args, **kwargs)
        return self
        
    def __getattr__(self, attr):
        attr_1 = getattr(self._instance, attr)
        if inspect.ismethod(attr_1):
            return self.wrapFunc(attr_1)
        else:
            return attr_1
        
        
def methodWrap(wrapFunc):
    """
伯乐在线：Python高级特性（2）：Closures、Decorators和functools
有用 setattr 实现的类方法的装饰器
"""
    def decorator(cls):
        return CustomAttr(cls, wrapFunc)
    return decorator

    
# decos

def inc_one(func):
    # 等于是增长函数调用链条
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        return res + 1
    return wrapper


# before、after 装饰器可以用于测试用(测试环境的xx，修改测试参数)

def before(func):
    # 等于是增长函数调用链条
    @wraps(func)
    def wrapper(*args, **kwargs):
        # do something
        res = func(*args, **kwargs)
        return res 
    return wrapper


def after(func):
    # 等于是增长函数调用链条
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        # do something
        return res
    return wrapper


# 天然的几个切面：1，参数 2，返回值


def fronzen_args(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_f = copy.deepcopy(args)
        kwargs_f = copy.deepcopy(kwargs)
        return func(*args_f, **kwargs_f)
    return wrapper


def func_hook(hook):
    # 等于是增长函数调用链条
    def decorated(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # do something
            return hook(func, *args, **kwargs)
        return wrapper
    return decorated

    
def invoking_warning(warnings):
    def decorated(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print warnings
            return func(*args, **kwargs)
        return wrapper
    return decorated


