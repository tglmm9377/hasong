from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods import models
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.
# /cart/add
class CartAddView(View):
    def post(self,request):
        '''购物车记录的添加'''
        #数据校验
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':"请先登录"})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id,count]):
            return JsonResponse({'res':0,'errmsg':'数据不完整'})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':0,'errmsg':"数量出错"})
        #校验商品是否存在
        try:
            sku = models.GoodsSKU.objects.get(id=sku_id)
        except models.GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res':0,'errmsg':"商品不存在"})


        #添加记录
        user = request.user
        connection = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        #如果hget查找的键不存在返回None
        cart_count = connection.hget(cart_key,sku_id)
        if cart_count:
            #累加
            count = count + int(cart_count)
            # 设置
        #校验商品库存
        if count > sku.stock:
            return JsonResponse({'res':0,'errmsg':"库存不足"})
        #属性存在就更新，如果不存在会添加
        print(cart_key,sku_id,count)
        connection.hset(cart_key,sku_id,count)
        cart_count = connection.hlen(cart_key)
        print(cart_count)
        return JsonResponse({'res':1,'cart_count':cart_count,'errmsg':"添加成功"})


class CartListView(LoginRequiredMixin,View):
    #前端传递的我数据
    def get(self,request):
        user = request.user
        #获取用户存在redis中的所有商品
        #用户id cart_user.id
        cart_key = 'cart_%d'%user.id
        connection = get_redis_connection('default')
        all  = connection.hgetall(cart_key)
        str_skus = ""
        sku_list= []
        for key in all.keys():
            # print(key,value)
            sku_list.append(key)
            print(key)
        sku = models.GoodsSKU.objects.filter(id__in=sku_list)
        str_skus = ",".join(str(i.decode()) for i in sku_list)
        total_count = 0
        for obj in sku:
            obj.count = connection.hget(cart_key,obj.id).decode()
            total_count = int(obj.count) + total_count


        context = {
            'skus':sku,
            'all':all,
            'total_count':total_count,
            "str_skus":str_skus,
        }

        return render(request,'cart_list.html',context)
class CartUpdate(View):
    def post(self,request):
        print('update')
        user = request.user
        # 获取ajax传递的数据 sku_id count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        print(sku_id,count)
        if not all([sku_id,count]):
            return JsonResponse({'res':0,'errmsg':"数据错误"})
        if count.isdigit():
           count = int(count)
        else:
            return JsonResponse({'res':0,'errmsg':"数量传递错误"})
        #判断sku是否存在
        try:
            sku = models.GoodsSKU.objects.get(id=int(sku_id))
        except models.GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res':0,'errmsg':"sku不存在"})
        #将数据更新到redis
        cart_key = 'cart_%d'%user.id
        connection = get_redis_connection('default')
        connection.hset(cart_key,sku_id,count)
        return JsonResponse({'res':1,'errmsg':"更新数据成功"})

class DeleteView(View):
    def post(self,request):
        user = request.user
        #数据合法校验
        sku_id = request.POST.get('sku_id')
        try:
            sku_id = int(sku_id)
        except Exception as e:
            return JsonResponse({'res':0,'errmsg':"sku_id错误"})
        cart_key = 'cart_%d'%user.id
        connection = get_redis_connection('default')
        connection.hdel(cart_key,sku_id)
        return JsonResponse({'res':1,'errmsg':"success"})
