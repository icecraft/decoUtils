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
import pprint


__all__ = ['immutableattr', 'safe_run', 'safe_run_dump', 'trace',
           'lineTrace', 'dump_args', 'delayRetry', 'logWrap', 'methodWrap',
           'test_run', 'timecal', 'profileit']


def _backtrace_f(f):
    while f:
        print f, f.f_code
        f = f.f_back


def profileit(func):
    def wrapper(*args, **kwargs):
        datafn = func.__name__ + ".profile"  # Name the data file sensibly
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        prof.dump_stats(datafn)
        return retval
    return wrapper


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
            _backtrace_f(sys._getframe())
            return None
    return wrapper


def trace(func):
    save_trace = []
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            save_trace.append(sys.gettrace())
            import pdb
            pdb.set_trace()
            res = func(*args, **kwargs)
            sys.settrace(save_trace[-1])
            return res
        except:
            sys.settrace(None)
    return wrapper


def lineTrace(f):
    """ copy this function from  
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return localtrace
        return None

    def localtrace(frame, why, arg):
        if why == "line":
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            bname = os.path.basename(filename)
            print "{}({}): {}".format(bname,
                                      lineno,
                                      linecache.getline(filename, lineno)),
        return localtrace
    
    @wraps(f)
    def _f(*args, **kwds):
        save_trace.append(sys.gettrace())
        sys.settrace(globaltrace)
        result = f(*args, **kwds)
        sys.settrace(save_trace[-1])
        return result

    return _f


def _filter_frame_dict(ddata):
    from inspect import isfunction, ismethod, ismodule

    no_private = lambda key: not key.startswith('_')  
    no_function = lambda key: not isfunction(ddata[key])
    no_method = lambda key: not ismethod(ddata[key])
    no_module = lambda key: not ismodule(key)
    no_ipython = lambda key: (key != 'In') and ( key != 'Out') \
                         and (key != 'exit') and (key !='quit')  
    
    filter_list = [no_private, no_function, no_method, no_module, no_ipython]
    return {key: ddata[key] for key in
            reduce(lambda r, x: filter(x, r), filter_list, ddata)}


def _diff_dict(new, old):

    _newkey_dict = {key: new[key] for key in (new.viewkeys() - old.viewkeys())}
    _diff_dict = {key: new[key] for key in (new.viewkeys() & old.viewkeys())
                  if new[key] != old[key]}
    _diff_dict.update(_newkey_dict)
    return _diff_dict
    

def lineDump(f):
    """ copy this function from  
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
 """
    save_trace = []
    pp = pprint.PrettyPrinter(indent=4)
    _frame_dict = []
    
    def globaltrace(frame, why, arg):
        if why == "call":
            return _dump
        return None

    def _print(ddata):
        if len(ddata) is 0:
            return
        pp.pprint(ddata)
        
    def _dump(frame, why, arg):
        if why == "line":
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            bname = os.path.basename(filename)
            """
            print "{}({}): {}".format(bname,
                                      lineno,
                                      linecache.getline(filename, lineno))"""
            
            f_locals, f_globals = _filter_frame_dict(frame.f_locals), _filter_frame_dict(frame.f_globals)

            if len(_frame_dict) == 0:
                pp.pprint(f_locals)
                pp.pprint(f_globals)
            else:
                _print(_diff_dict(f_globals, _frame_dict.pop()))
                _print(_diff_dict(f_locals, _frame_dict.pop()))
                
            _frame_dict.append(f_locals)
            _frame_dict.append(f_globals)
                
        return _dump
    
    @wraps(f)
    def _f(*args, **kwds):
        save_trace.append(sys.gettrace())
        sys.settrace(globaltrace)
        result = f(*args, **kwds)
        sys.settrace(save_trace[-1])
        return result

    return _f


def dump_args(func):
    """This decorator dumps out the arguments passed to 
a function before calling it and this code was copy from 
https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
"""
    
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        print fname, ":", ', '.join(
            '%s=%r' % entry
            for entry in zip(argnames, args) + kwargs.items())
        return func(*args, **kwargs)

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


def logWrap(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        logging.error('now enter')
        res = func(*args, **kwargs)
        logging.error('now exit')
        return res
    return wrap


class CustomAttr:
    def __init__(self, obj, wrapFunc=logWrap):
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

    
@methodWrap(logWrap)
class B(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def ad1(self, x):
        return x + 1

