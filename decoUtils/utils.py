# -*- coding: utf-8 -*-
import cPickle
import pprint


def backtrace_f(f):
    while f:
        print f, f.f_code
        f = f.f_back

        
def args_have_dict(*args):
    return any(map(lambda x: isinstance(x, dict), args))
        

def memorized_args_key(func, *args, **kwargs):
    arg_names = func.func_code.co_varnames
    arg_count = func.func_code.co_argcount
    
    arg_dict = {}
    for i, arg in enumerate(args[:arg_count]):
        arg_dict[arg_names[i]] = args[i]
    arg_dict.update({"*args": args[arg_count:]})
    arg_dict.update(**kwargs)
    return cPickle.dumps(arg_dict)
        

def filter_frame_dict(ddata):
    from inspect import isfunction, ismethod, ismodule, isclass

    no_private = lambda key: not key.startswith('_')  
    no_function = lambda key: not isfunction(ddata[key])
    no_method = lambda key: not ismethod(ddata[key])
    no_module = lambda key: not ismodule(ddata[key])
    no_class = lambda key: not isclass(ddata[key])
    no_type = lambda key: not (type(ddata[key]) == type)
    
    no_ipython = lambda key: (key != 'In') and ( key != 'Out') \
                         and (key != 'exit') and (key !='quit')  
    
    filter_list = [no_private, no_function, no_method, no_module,
                   no_ipython, no_type]
    
    return {key: ddata[key] for key in
            reduce(lambda r, x: filter(x, r), filter_list, ddata)}


def diff_dict(new, old):

    _newkey_dict = {key: new[key] for key in (new.viewkeys() - old.viewkeys())}
    _diff_dict = {key: new[key] for key in (new.viewkeys() & old.viewkeys())
                  if new[key] != old[key]}
    _diff_dict.update(_newkey_dict)
    return _diff_dict


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


def lineDumpFunc():
    def _print(ddata):
        if len(ddata) is 0:
            return
        safe_do_with_info(pp.pprint, ddata)

    _frame_dict = []
    pp = pprint.PrettyPrinter(indent=4)
    
    def _func(frame):
        f_locals, f_globals = map(filter_frame_dict,
                                  [frame.f_locals, frame.f_globals])

        try:
            _print(diff_dict(f_globals, _frame_dict.pop()))
            _print(diff_dict(f_locals, _frame_dict.pop()))
        except:
            _print(f_locals)
            _print(f_globals)
            
        _frame_dict.append(f_locals)
        _frame_dict.append(f_globals)
    return _func


