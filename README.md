# decoUtils 
collection of my python decorate code 
希望最终能收集 100 个 deco func !!

## 待增加功能
* lineDump: dump 出 frame 对象的 f_locals、f_globals # 第一次dump 出所有的值，后续的 dump 出变化的值 #done
* btDump: dump 出当前函数的调用栈.可以根据参数决定是否 dump 出每个 frame 的 f_locals、f_globals  #done
* profile 装饰器    # Done
* color output 装饰器   # noNeed

## 待考虑问题
* 如何用装饰器或者从 aop 面向切面编程观点出发，实现一个具有 mock anything 的工具
* 如何用装饰器实现 event-driven programming (参考python 库 blinker )


