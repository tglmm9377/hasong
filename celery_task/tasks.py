from celery import Celery
from django.core.mail import send_mail
from shennxian import settings
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shennxian.settings")
django.setup()
from django_redis import get_redis_connection
from django.shortcuts import render
from  django.template import loader

#创建Celery对象
app = Celery('celery_task.tasks',broker='redis://192.168.107.132:6379/8')

#定义任务函数
@app.task
def send_register_active_email(to_email,username,token):
    '''发送邮件'''
    # 发邮件
    subject = '来自tglmm的问候'
    message = '<h1>尊敬的%s,欢迎来到tglmm世界</h1>点击链接激活账号<a href="http://192.168.0.101:8000/user/active/%s">激活账号</a>' % (
    username, token)
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    send_mail(subject, message, sender, receiver, html_message=message)

@app.task
def generate_index_page():
    # 商品分类
    from goods import models
    types = models.GoodsType.objects.all()

    # 降序('-index')
    IndexGoodsBanner = models.IndexGoodsBanner.objects.all().order_by('index')

    promotion_banner = models.IndexPromotionBanner.objects.all().order_by('index')

    for type in types:
        image_banner = models.IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
        title_banner = models.IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)
        # 将取出的对象直接注入到type中
        type.image_banner = image_banner
        type.title_banner = title_banner
    context = {
        'types': types,
        "IndexGoodsBanner": IndexGoodsBanner,
        "promotion_banner": promotion_banner,
    }
    print("promotion_banner",promotion_banner)
    #加载模板,返回模板对象
    temp = loader.get_template('static_index.html')
    #定义模板上下文
    # context = RequestContext(request,context)
    #模板渲染
    static_index = temp.render(context)
    #生成静态页面
    import os
    save_path = os.path.join(settings.BASE_DIR,'static/index.html')
    # import sys,io
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gbk')
    with open(save_path,'w',encoding='utf-8') as f:
        f.write(static_index)
