import asyncio
import orm
from models import User

# 测试插入
@asyncio.coroutine
def test_save(loop):
    yield from orm.create_pool(loop, user='www-data', password='www-data', database='awesome')
    u = User(user_name='赵凯', user_id='016878',
             passwd='123456')
    # pdb.set_trace()
    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test_save(loop))
__pool = orm.__pool
__pool.close()  # 需要先关闭连接池
loop.run_until_complete(__pool.wait_closed())
loop.close()




