#定义一个索引类
from haystack import indexes
from goods.models import GoodsSKU

#指定为某个类某些数据建立索引
class GoodsSKUIndex(indexes.SearchIndex,indexes.Indexable):
    text = indexes.CharField(document=True,use_template=True)

    def get_model(self):
        return GoodsSKU
    #这个方法返回的内容将内容作为索引
    def index_queryset(self, using=None):
        return self.get_model().objects.all()

