from django.shortcuts import render,HttpResponseRedirect as redirect
from django.urls import reverse
from django.db import transaction
from django.http import JsonResponse
# Create your views here.
from alipay import AliPay,ISVAliPay
from django.views import View
from order import models
from user import models as user_models
from goods import models as goods_models
import os
from django_redis import get_redis_connection
from django import conf
from django.db import transaction
# /order

class OrderView(View):
    def post(self,request):
        #判断用户是否登录
        print('结算')
        user = request.user
        if not user.is_authenticated:
            return redirect(reverse("user:login"))
        #获取数据

        #用户的地址信息
        try:
            user = user_models.User.objects.get(id=user.id)
            address = user_models.Address.objects.filter(user=user)
        except user_models.Address.DoesNotExist as e:
            return render(request,'order_list.html',{'res':0,"msg":"没有地址信息，请添加地址"})
        #动态添加属性
        default_address = user_models.Address.objects.get_default_address(user)
        #商品信息 sku_id,数量从redis中获取，价格从数据库中获取
        sku_ids = request.POST.get('skus')
        print(sku_ids)
        sku_id_list = sku_ids.split(',')
        try:
            skus = goods_models.GoodsSKU.objects.filter(id__in=sku_id_list)
        except goods_models.GoodsSKU.DoesNotExist as e:
            return render(request,'order.html',{"res":0,"msg":"商品不存在"})

        #计算总价格
        total_count = 0
        total_amount = 0
        cart_key = "cart_%d"%user.id
        connection = get_redis_connection('default')
        for sku in skus:
            #获取数量
            count = int(connection.hget(cart_key,sku.id))
            sku.count = count
            price = sku.price
            amount = count * price
            total_count = total_count + count
            total_amount = total_amount + amount
        # connection.hset('order_%s'%user.id,)


        context = {
            "skus": skus,
            "total_amount":total_amount,
            "total_count":total_count,
            'address':address,
            "default_address":default_address,
            'sku_ids':sku_ids,
        }
        return render(request,'order_list.html',context)

class CommitView(View):
    # @transaction.automic
    def post(self,request):
        #判断是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({"res":0,"msg":"请先登录"})
        #获取信息 校验
        addr_id = request.POST.get('addr_id')
        sku_ids = request.POST.get('sku_ids')
        pay_style = request.POST.get("pay_style")
        if not all([addr_id,sku_ids,pay_style]):
            return JsonResponse({'res':0,'msg':"数据不完整"})
        #地址校验
        try:
            address = user_models.Address.objects.get(id=addr_id,user=user)
        except user_models.Address.DoesNotExist as e:
            return JsonResponse({'res': 0, 'msg': "地址信息有误"})
        #商品信息校验
        sku_id_list = sku_ids.split(',')
        print(sku_id_list)
        try:
            skus = goods_models.GoodsSKU.objects.filter(id__in=sku_id_list)
        except goods_models.GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res': 0, 'msg': "商品信息有误"})

        connection = get_redis_connection('default')
        cart_key = 'cart_%s'%user.id
        import time
        time.sleep(10)
        total_count = 0
        total_amount = 0
        for sku in skus:
            #获取数量
            count = connection.hget(cart_key,sku.id)
            print(count)
            sku.count = int(count)
            price = sku.price
            amount = sku.count * price
            total_count = total_count + sku.count
            total_amount = total_amount + amount
            sku.old_stock = sku.stock
            print('old_stock',sku.old_stock)
        #创建OrderInfo对象
        from datetime import datetime
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        order = models.OrderInfo.objects.create(order_id=order_id,
                                                user=user,
                                                addr=address,
                                                pay_method=int(pay_style),
                                                total_count=total_count,
                                                total_price=total_amount,
                                                transit_price=10,
                                                order_status=1
                                                )
        #乐观锁
        #创建订单商品表
        for sku in skus:
            order_goods = models.OrderGoods.objects.create(order=order,
                                                           sku=sku,
                                                           count=sku.count,
                                                           price=sku.price,
                                                           comment=""
                                                       )
            #更新商品表的库存数据，判断和之前的库存数据是否相同
            update_goods = goods_models.GoodsSKU.objects.get(id=sku.id,stock=sku.old_stock)
            update_goods.stock = sku.old_stock - sku.count
            update_goods.sales =  update_goods.sales + sku.count
            print("用户：%s 商品id:%d 先前的库存:%d 当前的库存%d"%(user.username,sku.id,sku.old_stock,update_goods.stock))
            update_goods.save()
        #如果以上都不误，说明订单创建成功，删除购物车内对应的数据
        return JsonResponse({'res':1,'msg':"创建订单成功"})



class OrderPay(View):
    '''订单支付'''
    def post(self,request):
        #用户是否登录
        user = request.user
        #接收参数
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res':1,'errmsg':"无效的订单id"})
        try:
            #满足的条件包括 订单id 用户 支付方式 支付状态
            order = models.OrderInfo.objects.get(order_id=order_id,
                                                 user=user,
                                                 pay_method=3,
                                                 order_status=1
                                                 )
        except models.OrderInfo.DoesNotExist as e:
            return JsonResponse({'res':1,'errmsg':"订单错误"})
        #业务处理

        alipay = AliPay(
            appid="2016102200737964",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=os.path.join(conf.settings.BASE_DIR,'apps/order/alipay_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=os.path.join(conf.settings.BASE_DIR,'apps/order/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True  # 默认False
        )
        #调用支付接口
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no="20161112",
            total_amount=0.01,
            subject="daydayfresh",
            return_url="",
            notify_url=""  # 可选, 不填则使用默认notify url
        )
        #返回
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res':3,'pay_url':pay_url})

class CheckPayView(View):
    def post(self,request):
        # 用户是否登录
        user = request.user
        # 接收参数
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': "无效的订单id"})
        try:
            # 满足的条件包括 订单id 用户 支付方式 支付状态
            order = models.OrderInfo.objects.get(order_id=order_id,
                                                 user=user,
                                                 pay_method=3,
                                                 order_status=1
                                                 )
        except models.OrderInfo.DoesNotExist as e:
            return JsonResponse({'res': 1, 'errmsg': "订单错误"})
        # 业务处理

        alipay = AliPay(
            appid="2016102200737964",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=os.path.join(conf.settings.BASE_DIR, 'apps/order/alipay_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=os.path.join(conf.settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        #调用支付宝交易查询接口
        while True:
            query = alipay.api_alipay_trade_query(out_trade_no=order_id)
            code = query.get('code')
            trade_status = query.get('trade_status')
            if code == '10000' and trade_status == "TRADE_SUCCESS":
                #支付成功
                trade_no = query.get('trade_no')
                #改变订单 状态
                order.trade_no = trade_no
                order.trade_status = '待评价'
                order.save
                # 返回结果
                return JsonResponse({'res':0,'msg':"支付成功"})
            elif code == '10000' and trade_status == "WAIT_BUYER_PAY":
                #待付款
                import time
                time.sleep(5)
                continue
            #订单超时
            else:
                return JsonResponse({'res':1,'msg':"支付失败"})






