from django.shortcuts import render,HttpResponseRedirect as redirect
import re
from user import models
from goods.models import GoodsSKU
# Create your views here.
from django.shortcuts import resolve_url
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from shennxian import settings
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.core.mail import send_mail
from celery_task import tasks
from django.contrib.auth import authenticate,login
from utils.mixin import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

def register(request):
    '''显示注册页面'''
    return render(request,'register.html')

def register_handle(request):
    '''注册处理'''
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')
    #数据校验
    if not all([username,password,email]):
        #数据不完整
        return render(request,'register.html',{'errmsg':'数据不完整'})
    # if not re.match(r'/^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$/',email):
    #     return render(request,'register.html',{'errmsg':"邮箱格式错误"})
    if allow != "on":
        return render(request,'register.html',{'errmsg':"请同意协议"})
    try:
        user = models.User.get(username=username)

    except models.User.DoesNotExist:
        #用户不存在
        user = None
    if user:
        return render(request,'register.html',{'errmsg':'用户名已经存在'})

    user = models.User.objects.create_user(username,email,password)
    user.is_active = 0
    user.save()

    return redirect(resolve_url('goods:index'))

#类视图使用
class RegisterView(View):
    '''注册'''
    def get(self,request):
        '''页面显示'''
        return render(request,'register.html')
    def post(self,request):
        '''注册处理'''
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # if not re.match(r'/^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$/',email):
        #     return render(request,'register.html',{'errmsg':"邮箱格式错误"})
        if allow != "on":
            return render(request, 'register.html', {'errmsg': "请同意协议"})
        try:
            user = models.User.objects.get(username=username)

        except models.User.DoesNotExist:
            # 用户不存在
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已经存在'})

        user = models.User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        #加密用户的ID
        serializer = Serializer(settings.TOKEN_OF_ACTIVE,3600)
        token = serializer.dumps({'confirm':user.id}).decode()
        #发邮件
        tasks.send_register_active_email.delay(email,username,token)

        return redirect(resolve_url('goods:index'))

class ActiveView(View):
    def get(self,request,token):
        #解密
        print('token:'+token)
        serializer = Serializer(settings.TOKEN_OF_ACTIVE,3600)

        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = models.User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            #跳转到登录页面
            return redirect(resolve_url('user:login'))
        except SignatureExpired as e:
            #实际项目中应该添加重新激活的链接
            return HttpResponse('激活链接已经过期')


class LoginView(View):
    def get(self,request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            print(username)
            #查看到cookie中有username属性，就将checkbox记住用户名勾选状态
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request,'login.html',{'username':username,'checked':checked})

    def post(self,request):
        '''登录校验'''
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        print(username,password)
        if not all([username,password]):
            return render(request,'login.html',{'errmsg':'数据不完整'})
        #django自带的认证方法
        user = authenticate(username=username,password=password)
        print(user)
        if user is not None:
            if True:
                #认证通过
                login(request,user)
                #默认值设置
                next_url = request.GET.get('next',resolve_url("goods:index"))
                #判断是否记住用户名
                print(next_url)
                response = redirect(next_url)
                remember =  request.POST.get('remember')
                print('remember',remember)
                if remember:
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response

            else:
                #用户存在但是未激活
                return render(request, 'login.html', {'errmsg': "用户未激活"})
        else:
            return render(request,'login.html',{'errmsg':"用户不存在"})

class UserInfoView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        address_obj = models.Address.objects.get_default_address(user)
        if not address_obj:
            address_obj = ""
        # print(address_obj.addr)
        #获取用户的历史浏览记录
        from django_redis import get_redis_connection
        con = get_redis_connection('default')
        history_key = 'history_%d'% user.id
        #获取用户最新浏览的五条商品
        sku_ids = con.lrange(history_key,0,4)
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        return render(request,'info.html',{'address_obj':address_obj,'goods_list':goods_li})

class UserOrderView(LoginRequiredMixin,View):
    def get(self,request):
        return render(request,'order.html')



class AddressView(LoginRequiredMixin,View):
    '''显示用户地址也'''
    def get(self,request):
        user = request.user
        address = models.Address.objects.get_default_address(user)
        if not address:
            msg = "默认地址不存在"
        else:
            msg = ""
        return render(request,'address.html',{'msg':msg,'address':address})

    def post(self,request):
        receiver = request.POST.get('receiver')
        phone = request.POST.get('phone')
        zip_code = request.POST.get('zip_code')
        addr = request.POST.get('address')
        print(addr)
        #数据校验
        if not all([receiver,phone,addr]):
            return render(request,'address.html',{'errmsg':'信息输入不完整'})
        #校验手机号

        ret = re.match(r"1[35678]\d{9}", phone)
        if not ret:
            return render(request, 'address.html', {'errmsg': '手机号码不正确'})
        user = request.user
        address = models.Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        addr =  models.Address.objects.create(user=user,
                                              addr = addr,
                                              receiver=receiver,
                                              # zip_code = zip_code,
                                              phone = phone,
                                              is_default = is_default
                                              )
        return redirect(resolve_url('user:address'))
            # return render(request,'address.html')


from django.contrib.auth import logout

class LogoutView(View):
    def get(self,request):
        logout(request)
        '''跳转到首页'''
        return redirect(resolve_url("user:login"))



class CartView(LoginRequiredMixin,View):
    def get(self,request):
        pass

