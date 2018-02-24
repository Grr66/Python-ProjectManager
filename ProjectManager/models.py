import uuid

from orm import Model, StringField, FloatField
import time

def next_id():
    # 当前时间再集合uuid4就不会产生重复ID的问题了
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'user'
    user_id = StringField(primary_key=True,ddl='varchar(6)')
    passwd = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varcahr(10)')
    created_at = FloatField(default=time.time)
    admin =  StringField(ddl='varchar(1)')

class Project(Model):
    __table__ = 'project'
    project_id = StringField(primary_key=True,ddl='varchar(14)')#项目编号
    project_name = StringField(ddl='varchar(100)')#项目名称
    project_level = StringField(ddl='varchar(1)')  # 项目阶段 项目级别
    project_status = StringField(ddl='varchar(1)')#项目状态 启动/暂停
    project_stage = StringField(ddl='varchar(1)')#项目阶段 需求/开发/技术测试/准生产测试/投产/完结
    project_docFlag = StringField(ddl='varchar(1)')#项目文档是否齐全
    #project_department = StringField(ddl='varchar(20)')#项目提出部门
    #project_resource = StringField(ddl='varchar(100)')#项目人员
    #project_environment = StringField(ddl='varchar(100)')#项目环境
    created_at = FloatField(default=time.time)
    project_manager = StringField(ddl='varcahr(10)')