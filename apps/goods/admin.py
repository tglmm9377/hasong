from django.contrib import admin
from goods import models
# Register your models here.



class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''新增更新表中的数据时候调用'''
        #先使用父类中的方法将数据进行更新
        super().save_model(request,obj,form,change)
        #附加操作重新生成首页静态页面
        from celery_task.tasks import generate_index_page
        generate_index_page.delay()

    def delete_model(self, request, obj):
        super().delete_model(request.obj)
        from celery_task.tasks import generate_index_page
        generate_index_page.deplay()
class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass




admin.site.register(models.Goods)
admin.site.register(models.GoodsType)
admin.site.register(models.IndexGoodsBanner)
admin.site.register(models.GoodsSKU)
admin.site.register(models.IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(models.IndexTypeGoodsBanner)
