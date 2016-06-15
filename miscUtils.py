# -*- coding: utf-8 -*-


def safe_do(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except:
        pass

    
def safe_do_with_info(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except:
        print func

        

    
