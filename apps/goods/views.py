from django.shortcuts import render,HttpResponseRedirect as redirect
from django.views import View
from goods import models
from django_redis import get_redis_connection
from django.core.cache import cache
from django.urls import reverse
from order.models import OrderGoods
from utils.mixin import LoginRequiredMixin
from django.core.paginator import Paginator

# Create your views here.
class IndexView(View):
    def get(self,request):
        #商品分类
        context = cache.get('index_cache_page1')
        if not context:
            types = models.GoodsType.objects.all()

            #降序('-index')
            IndexGoodsBanner = models.IndexGoodsBanner.objects.all().order_by('index')

            promotion_banner = models.IndexPromotionBanner.objects.all().order_by('index')

            for type in types:
                image_banner = models.IndexTypeGoodsBanner.objects.filter(type=type,display_type=1)
                title_banner = models.IndexTypeGoodsBanner.objects.filter(type=type,display_type=0)
                #将取出的对象直接注入到type中
                # print(type.name,image_banner)
                type.image_banner = image_banner
                # print(type.image_banner)
                type.title_banner = title_banner

            context = {
                'types': types,
                "IndexGoodsBanner": IndexGoodsBanner,
                "promotion_banner": promotion_banner,
            }
            for ttt in types:
                for aaa in ttt.image_banner:
                    print(aaa.type.name)

            # print('types')
            #设置缓存
            # print('设置缓存',context)
            cache.set('index_cache_page',context,1)

        user = request.user
        cart_count = 0
        if user.is_authenticated:
            connetction = get_redis_connection('default')
            # print('cart_'+str(user.id))
            cart_count = connetction.hlen('cart_'+str(user.id))

        context['cart_count'] = cart_count
        # print(context)
        return render(request, 'index.html', context)

class DetailView(View):
    def get(self,request,goods_id):
        try:
           sku = models.GoodsSKU.objects.get(id=goods_id)
        except models.GoodsSKU.DoesNotExist as e:
            #商品不存在
            return redirect(reverse('goods:index'))
        #获取商品的种类信息
        types = models.GoodsType.objects.all()
        #获取商品的评论信息
        # sku_orders = OrderGoods.objects.get(sku=sku).exclude(comment="")
        #获取新品信息
        new_goods = models.GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[0:2]
        #获取商品的其他规格
        goods_spu = models.GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku.id)

        #购物车信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            connetction = get_redis_connection('default')
            # print('cart_'+str(user.id))
            cart_count = connetction.hlen('cart_' + str(user.id))

            #添加用户的历史浏览记录
            connection = get_redis_connection('default')
            history = "history_%d"%user.id
            connetction.lrem(history,0,goods_id)
            connetction.lpush(history,goods_id)
            connetction.ltrim(history,0,4)
        context = {
            "types":types,
            "new_skus":new_goods,
            "sku_orders":"",
            "sku":sku,
            "goods_spu":goods_spu,
            "cart_count":cart_count,

        }
        return render(request,'detail.html',context)

class ListView(View):
    def get(self,request,type_id,page):

        #检查type_id 合法性

        try:
            # 当前所有商品的种类
            type = models.GoodsType.objects.get(id=int(type_id))

        except models.GoodsType.DoesNotExist as e:
            #没有此种类型直接重定到主页
            print('not found type',type_id)
            return redirect(reverse('goods:index'))

        types = models.GoodsType.objects.all()
        #所有商品分类信息

        sort = request.GET.get('sort')
        if sort == "price":
            skus = models.GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == "hot":
            skus = models.GoodsSKU.objects.filter(type=type).order_by('-sales')
        #根据当前所选商品种类查询所有这这类商品信息
        else:
            skus = models.GoodsSKU.objects.filter(type=type)
            sort = "default"


        #新品信息查询
        new_skus = models.GoodsSKU.objects.filter(type=type).order_by('create_time')[0:2]
        #购物车数量信息
        user = request.user
        if user.is_authenticated:
            connection = get_redis_connection('default')
            cart_count = connection.hlen('cart_'+str(user.id))
        #分页显示
        page_obj = Paginator(skus,1)
        #判断page合法性,容错处理
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > page_obj.num_pages:
            page = 1
        page_list = page_obj.page(page)

        #分页控制
        '''
        1 2 3 4 5
        2 3 4 5 6
        3 4 5 6 7
        当前页page
        1.总的页码数小于等于n
        2.如果当前页小于等于n/2+1
        3.如果当前页面大n/2+1
        '''
        per_page = 5
        n = per_page/2 + 1
        num_pages = page_obj.num_pages
        print(num_pages)
        if page <= num_pages:
            pages = range(1,num_pages+1)
        elif page > n:
            pages = range(page-(n-1),page+n)
        elif num_pages - page < n-1:
            pages = range(num_pages-per_page+1,num_pages+1)






        context = {
            "type":type,
            "types":types,
            "page_list": page_list,
            "new_skus":new_skus,
            "cart_count":cart_count,
            'page':page,
            "sort":sort,
            'pages':pages
        }
        print(pages)
        return render(request,'list.html',context)
