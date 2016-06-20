# decoUtils 
collection of my python decorate code 
希望最终能收集 100 个 deco func !!

## 待增加功能
1. lineDump: dump 出 frame 对象的 f_locals、f_globals # 第一次dump 出所有的值，后续的 dump 出变化的值 #done
   * dump 出函数体内调用的其他函数
   * lineDump: 默认的处理函数不能进入 try: except 块内  

2. btDump: dump 出当前函数的调用栈.可以根据参数决定是否 dump 出每个 frame 的 f_locals、f_globals  #done
3. profile 装饰器    # Done
4. color output 装饰器   # noNeed
5. 当发生异常时，自动进入 pdb 
6. memorized 装饰器  # Done
7. memorized_timeout 装饰器  # Done
8. redis_retry 装饰器还是有些问题需要解决的
9. 简单的工作队列装饰器，如果一个函数在工作，则相关相关的参数保存下来。如果这个函数在工作，则将相关的任务塞 入到工作队列中。如果不是则直接执行并同时清空已有的工作中内容   # 并非所有场合都适用(如果机器性能低，可能会阻塞住，函数的参数不能过大)，用于装饰类方法  和闭包函数时可能有问题
10. 简单的 synchronized 装饰器 # Done 该装饰器的实现代码来自网络


## 待考虑问题
1. 如何用装饰器或者从 aop 面向切面编程观点出发，实现一个具有 mock anything 的工具
2. 如何用装饰器实现 event-driven programming (参考python 库 blinker )
3. 考虑待增加功能 9 中所遇到的问题，考虑用 blinker 等事件驱动的方式解决


## 待修改的问题
1. dump_args 无法打印 *args, **kwargs 参数、dump_args 不能和 dump_res 配合使用  #done






