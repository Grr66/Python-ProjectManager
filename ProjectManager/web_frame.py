# add_route函数，用来注册一个url处理函数
import asyncio
import inspect
from urllib import parse
import functools
from apis import APIError
from aiohttp import web
import os
import logging
logging.basicConfig(level=logging.INFO)  # 必须紧跟其后

# --------------get和post装饰器，用于增加__method__和__route__特殊属性，分别标记GET,POST方法和path
def get(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        #装饰后添加_method_和_route_这两个属性
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        #装饰后添加_method_和_route_这两个属性
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# add_route函数，用来注册一个url处理函数
#app是响应函数集合，fn是要调用的处理函数
def add_route(app,fn):
    # 获取'__method__'和'__route__'属性，如果有空则抛出异常
    method = getattr(fn,'__method__',None)#提交方式get/post
    path = getattr(fn,'__route__',None)#url路径
    if path is None or method is None:
        raise ValueError('====>@GET OR @POST NOT DEFINED IN %S' % str(fn))
    # 判断fn是不是协程（即@asyncio.coroutine修饰的）并且判断是不是fn 是不是一个生成器(generator function)
    if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
        #都不是的话，强行修饰为协程
        fn = asyncio.coroutine(fn)
    logging.info('====>add route %s %s => %s (%s)' %( method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    # 正式注册为相应的url处理方法
    # 处理方法为RequestHandler的自省函数'__call__'
    app.router.add_route(method,path,RequestHandler(app,fn))##把响应函数添加到响应函数集合

#可以批量注册的函数，预期效果是：只需向这个函数提供要批量注册函数的文件路径，新编写的函数就会筛选，注册文件内所有符合注册条件的函数。
#app响应函数集合，module_name处理函数路径
def add_routes(app, module_name):
    # 自动搜索传入的module_name的module的处理函数
    # 检查传入的module_name是否有'.'
    # Python rfind() 返回字符串最后一次出现的位置，如果没有匹配项则返回-1
    n = module_name.rfind('.')
    logging.info('n = %s', n)
    # 没有'.',则传入的是module名
    # __import__方法使用说明请看：http://kaimingwan.com/post/python/python-de-nei-zhi-han-shu-__import__
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
        logging.info('globals = %s', globals()['__name__'])
    else:
        # name = module_name[n+1:]
        # mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
        # 上面两行是廖大大的源代码，但是把传入参数module_name的值改为'handlers.py'的话走这里是报错的，所以改成了下面这样
        mod = __import__(module_name[:n], globals(), locals())
    # 遍历mod的方法和属性,主要是招处理方法
    # 由于我们定义的处理方法，被@get或@post修饰过，所以方法里会有'__method__'和'__route__'属性
    for attr in dir(mod):
        # 如果是以'_'开头的，一律pass，我们定义的处理方法不是以'_'开头的
        if attr.startswith('_'):
            continue
        # 获取到非'_'开头的属性或方法
        fn = getattr(mod, attr)
        # 取能调用的，说明是方法
        if callable(fn):
            # 检测'__method__'和'__route__'属性
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                # 如果都有，说明使我们定义的处理方法，加到app对象里处理route中
                add_route(app, fn)

# 添加静态页面的路径
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')#当前路径下的static文件夹
    app.router.add_static('/static',path)#app是aiohttp库里面的对象，通过router.add_router方法可以指定处理函数。本节代码自己实现了add_router。关于更多请查看aiohttp的库文档：http://aiohttp.readthedocs.org/en/stable/web.html
    logging.info('====>添加静态页面路径add static %s=> %s' % ('/static',path))

# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，
# 调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：
# app是响应函数集合 fn是要调用的处理函数handler
class RequestHandler(object):#初始化一个请求处理类
    def __init__(self,app,fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    # __call__方法的代码逻辑:
    # 1.定义kw对象，用于保存参数
    # 2.判断request对象是否存在参数，如果存在则根据是POST还是GET方法将参数内容保存到kw
    # 3.如果kw为空(说明request没有传递参数)，则将match_info列表里面的资源映射表赋值给kw；如果不为空则把命名关键字参数的内容给kw
    # 4.完善_has_request_arg和_required_kw_args属性
    @asyncio.coroutine
    def __call__(self,request):
        kw = None
        #确保有参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            #-----阶段1：post/get方法下正确解析request的参数，包括位置参数和关键字参数
            #POST提交请求的类型（通过content_type可以指定）
            if request.method == 'POST':
                # 判断是否存在Content-type(媒体格式类型)，一般content-type包含的值
                # text/html:charset:utf-8
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct = request.content_type.lower()
                # 如果请求为json的数据格式
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params,dict):#参数是否是dict格式，不是的话提示json body出错
                        return web.HTTPBadRequest(text='JSON BODY MUST BE OBJECT')
                    kw = params #把request的参数信息给kw
                # 如果POST提交请求类型
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = yield from request.post()#调用post方法，此处使用了装饰器
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupport Content-type:%s' % request.content_type)
            if request.method == 'GET':#get方法 直接后面跟了string来请求服务器上的资源
                qs = request.query_string
                logging.info('web_frame.requestHandler GET处理1====>：qsery_string=%s' % qs)
                if qs:
                    kw = dict()
                    #该方法解析url中？ 后面的键值对内容保存到kw中
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]
                    logging.info('web_frame.requestHandler GET处理2====>：kw=%s'%kw)
        if kw is None: # 参数为空说明没有从Request对象中获取到必要参数
            kw = dict(**request.match_info)# 此时kw指向match_info属性，一个变量标识符的名字的dict列表。Request中获取的命名关键字参数必须要在这个dict当中
            logging.info('web_frame.requestHandler====>:kw=%s'%kw)
        #kw 不为空时，还要判断是可变参数还是命名关键字参数，如果是命名关键字参数的，则需要remove all unamed kw，这是为啥？
        else:
            #如果从Request对象中获取到参数了
            #当没有可变参数，有命名关键字参数时候，kw指向命名关键字参数的内容
            if not self._has_var_kw_arg and self._named_kw_args:
                #remove all unamed kw :删除所有没有命名的关键字参数
                copy = dict()
                for name in  self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            #check named arg:检查命名关键字参数的名字是否和match_info中的重复
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)  # 命名参数和关键字参数有名字重复
                kw[k] = v
        # 如果有request这个参数，则把request对象加入kw['request']
        if self._has_request_arg:
            kw['request'] = request
        #check required kw :检查是否有必要关键字参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                if name not in kw:
                    return web.HTTPBadRequest(text='Missing argument:%s' % name)
        logging.info('call with args:%s' % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error,data=e.data,message=e.message)

# ---------------------------- 使用inspect模块中的signature方法来获取函数的参数，实现一些复用功能--
# 关于inspect.Parameter 的  kind 类型有5种：
# POSITIONAL_ONLY		只能是位置参数
# POSITIONAL_OR_KEYWORD	可以是位置参数也可以是关键字参数
# VAR_POSITIONAL			相当于是 *args
# KEYWORD_ONLY			关键字参数且提供了key，相当于是 *,key
# VAR_KEYWORD			相当于是 **kw
def get_required_kw_args(fn):
    #如果url处理函数需要传入关键字参数，且默认是空的话，获取这个key
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        # param.default == inspect.Parameter.empty这一句表示参数的默认值要为空
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    #如果url处理函数需要传入关键字参数，获取这个key
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)

def has_named_kw_args(fn):  # 判断是否有指定命名关键字参数
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_arg(fn):  # 判断是否有关键字参数，VAR_KEYWORD对应**kw
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 判断是否存在一个参数叫做request，并且该参数要在其他普通的位置参数之后，即属于*kw或者**kw或者*或者*args之后的参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # 只能是位置参数POSITIONAL_ONLY
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (
                fn.__name__, str(sig)))
    return found

