import hashlib

import time
from aiohttp import web
import asyncio

import json

import logging
from apis import APIValueError, APIError, APIResourceNotFoundError
from config import configs
from models import User, next_id, Project
from page import Page
from web_frame import get, post


#------------------------------------------------------------------------
#主页面
@get('/manage/projects')
def manage_projects(*,page='1'):
    return {
        '__template__': 'manage_projects.html',
        'page_index': get_page_index(page)
    }

#登陆页面
@get('/login')
def login():
    return {
        '__template__': 'login.html'
    }

#注册页面
@get('/register')
def register():
    return {
        '__template__':'register.html'
    }

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

# 根据用户信息拼接一个cookie字符串
def user2cookie(user, valid_time):
    # build cookie string by: id-expires-sha1
    # 过期时间是当前时间+设置的有效时间
    expires = str(int(time.time() + valid_time))
    print(time.localtime(time.time() + valid_time))
    # 构建cookie存储的信息字符串
    s = '%s-%s-%s-%s' % (user.user_id, user.passwd, expires, _COOKIE_KEY)
    L = [user.user_id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    # 用-隔开，返回
    return '-'.join(L)

# 根据cookie字符串，解析出用户信息相关的
@asyncio.coroutine
def cookie2user(cookie_str):
    # cookie_str是空则返回
    if not cookie_str:
        return None
    try:
        # 通过'-'分割字符串
        L = cookie_str.split('-')
        # 如果不是3个元素的话，与我们当初构造sha1字符串时不符，返回None
        if len(L) != 3:
            return None
        # 分别获取到用户id，过期时间和sha1字符串
        user_id, expires, sha1 = L
        # 如果超时，返回None
        if int(expires) < time.time():
            return None
        # 根据用户id查找库，对比有没有该用户
        user = yield from User.find(user_id)
        # 没有该用户返回None
        if user is None:
            return None
        # 根据查到的user的数据构造一个校验sha1字符串
        s = '%s-%s-%s-%s' % (user.user_id, user.passwd, expires, _COOKIE_KEY)
        # 比较cookie里的sha1和校验sha1，一样的话，说明当前请求的用户是合法的
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        # 返回合法的user
        return user
    except Exception as e:
        logging.exception(e)
        return None

#制作用户注册api
@post('/api/register_user')
async def api_register_usesr(*,user_id,user_name,passwd):
    if not user_name or not user_name.strip():#如果名字是空格或没有返错，这里感觉not name可以省去，因为在web框架中的RequsetHandler已经验证过一遍了
        raise APIValueError('user_name')
    if not user_id or not user_id.strip:
        raise APIValueError('user_id')
    if not passwd and not passwd.strip:
        raise APIValueError('password')
    users = await User.findAll(where='user_id=?', args=[user_id])#查询id是否已注册，查看ORM框架源码
    if len(users) > 0:
        raise APIError('register:failed','user_id','user_id is already in use.')
    #接下来就是注册到数据库上,具体看会ORM框架中的models源码
    #这里用来注册数据库表id不是使用Use类中的默认id生成，而是调到外部来，原因是后面的密码存储摘要算法时，会把id使用上。
    #uid = next_id()
    #sha1_passwd = '%s:%s' % (uid, passwd)
    sha1_passwd = '%s:%s' % (user_id, passwd)
    user = User(user_id=user_id, user_name=user_name.strip(), passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest())
    await user.save()
    #制作cookie返回浏览器客户端
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user,86400), max_age=86400, httponly=True)
    user.passwd = '******'#掩盖passwd
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


#验证登陆
@post('/api/login')
def api_login(*,user_id,passwd):
    #如果user_id和passwd为空，说明有错误
    if not user_id:
        raise APIValueError('user_id',"Invalid user_id")
    if not passwd:
        raise APIValueError('passwd','Invalid passwd')
    #根据uerid在库里查找匹配用户,返回结果是一个list
    query_result = yield from User.findAll('user_id=?',[user_id])
    #没找到用户返用户不存在
    if len(query_result) == 0:
        raise APIValueError('user_id','user_id not exist')
    #找到用户，将其取出，理论上只查找到一个
    user = query_result[0]

    #sha1摘要算法读取库里的密码
    # 按存储密码的方式获取出请求传入的密码字段的sha1值
    sha1 = hashlib.sha1()
    sha1.update(user.user_id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    #print('=====================sha1.hexdigest()',sha1.hexdigest())

    # 和库里的密码字段的值作比较，一样的话认证成功，不一样的话，认证失败
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd','Invalid passwd')
    # if user.passwd != passwd:
    #     raise APIValueError('passwd', 'Invalid passwd')
    # 构建返回信息
    r = web.Response()
    # 添加cookie
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)#86400单位是秒 代表1天
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

# 登出操作
@get('/logout')
def logout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    # 清理掉cookie得用户信息数据
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('====>user signed out')

    return r

@get('/manage/projects/create')
def manage_create_projects():
    # 新建项目页面
    return {
        '__template__': 'manage_project_create.html',
        'id': '',
        'action': '/api/projects/create'  # 对应HTML页面中VUE的action名字
    }

#创建项目
@post('/api/projects/create')
def api_create_project(request, *, project_id,project_name,project_level):
    # 只有管理员可以写博客
    #check_admin(request)
    #不能为空
    if not project_id or not project_id.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not project_name or not project_name.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    # 根据传入的信息，构建一条项目数据
    project = Project(
        project_id=project_id,
        project_name=project_name,
        #project_status=project_status,
        #project_stage=project_stage,
        #project_docFlag=project_docFlag,
        project_level=project_level,
        project_manager=request.__user__.user_name
        # project_department=project_department,
        # project_resource=project_resource,
        # project_environment=project_environment
    )
    p_r = yield from Project.findAll(where='project_id=?', args=[project_id])  # 查询id是否已注册，查看ORM框架源码
    if len(p_r) > 0:
        raise APIError('新建项目失败', 'project_id', 'project_id is already in use.')
    # 保存
    yield from project.save()
    return project

#展示项目首页
@get('/api/projects/show')
def api_show_projects(*,request, page='1'):
    # 获取项目信息
    page_index = get_page_index(page)
    num = yield from Project.findNumber('count(project_id)')
    p = Page(num, page_index, 5)
    if num == 0:
        return dict(page=p, projects=())
    projects = yield from Project.findAll('project_manager= ?',[request.__user__.user_name],orderBy='created_at asc', limit=(p.offset, p.limit))
    return dict(page=p, projects=projects)

# 获取页数，主要是做一些容错处理
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

#根据项目编号查看一条信息
@get('/project/{project_id}')
def get_project(project_id):
    # 根据博客id查询该条信息
    project = yield from Project.find(project_id)
    # # 根据博客id查询该条博客的评论
    # comments = yield from Comment.findAll('blog_id=?', [project_id], orderBy='created_at desc')
    # # markdown2是个扩展模块，这里把博客正文和评论套入到markdonw2中
    # for c in comments:
    #     c.html_content = text2html(c.content)
    # project.html_content = markdown2.markdown(project.content)
    # 返回页面
    return {
        '__template__': 'manage_project_query.html',
        'project': project
        #'comments': comments
    }

#修改一条项目信息
@get('/manage/projects/modify/{project_id}')
def manage_modify_project(project_id):
    # 修改项目信息的页面
    return {
        '__template__': 'manage_project_modify.html',
        'project_id': project_id,
        'action': '/api/projects/modify'
    }

@post('/api/projects/modify')
def api_modify_project(request, *, project_id,project_name,project_level,project_status,project_stage,project_docFlag,**kwargs):
    # 修改一条项目信息
    logging.info("====>api_modify_project:修改的项目编号为：%s", project_id)
    # name，id,level 不能为空
    if not project_name or not project_name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not project_level or not project_level.strip():
        raise APIValueError('level', 'level cannot be empty')
    if not project_id or not project_id.strip():
        raise APIValueError('project_id', 'project_id cannot be empty')

    # 获取指定id的project数据
    project_r = yield from Project.find(project_id)
    project_r.project_name = project_name
    project_r.project_level = project_level
    project_r.project_id = project_id
    project_r.project_status = project_status
    project_r.project_stage = project_stage
    project_r.project_docFlag = project_docFlag
    # 保存
    yield from project_r.update()
    return project_r

#修改的时候，会先调查询，反显
@get('/api/projects/get/{project_id}')
def api_get_project(*, project_id):
    # 获取某条项目的信息
    project = yield from Project.find(project_id)
    return project

@post('/api/projects/{project_id}/delete')
def api_delete_project(project_id, request):
    # 删除一条项目信息
    logging.info("====>api_delete_project:删除的项目ID为：%s" % project_id)
    # # 先检查是否是管理员操作，只有管理员才有删除评论权限
    # check_admin(request)
    # # 查询一下评论id是否有对应的评论
    p = yield from Project.find(project_id)
    # 没有的话抛出错误
    if p is None:
        raise APIResourceNotFoundError('Project')
    # 有的话删除
    yield from p.remove()
    return dict(project_id=project_id)

#用户信息查看模块
@get('/api/users')
def api_get_users(page='1'):
    # 返回所有的用户信息jason格式

    page_index = get_page_index(page)
    num = yield from User.findNumber('count(user_id)')
    p = Page(num, page_index, 10)#Page是一个分页类，系统内置的，(项目条数，首页定位，每页展示条数)
    if num == 0:
        return dict(page=p, users=())
    users = yield from User.findAll(orderBy='created_at desc')
    logging.info('users = %s and type = %s' % (users, type(users)))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)




@get('/manage/users')
def manage_users(*, page='1'):
    # 查看所有用户
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }