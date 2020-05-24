from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from db.base_model import BaseModel


class User(AbstractUser,BaseModel):
     '''用户模型类'''
     def generate_active_token(self):
         '''生成用户签名字符串'''
         serializer = Serializer(settings.TOKEN_OF_ACTIVE,10)
         info = {'confirm':self.id}
         token = serializer.dumps(info)
         return token.decode()

     class Meta:
         db_table = 'df_user'
         verbose_name = "用户"
         verbose_name_plural = verbose_name

class AddressManager(models.Manager):

    def get_default_address(self,user):
        try:
            address = self.get(user=user,is_default=True)
        except Address.DoesNotExist as e:
            address = None
        return address



class Address(BaseModel):
    '''
    账户 收件人 地址 电话 是否为默认地址
    '''
    user = models.ForeignKey('User',verbose_name="所属账户",on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20,verbose_name='收件人')
    addr = models.CharField(max_length=256,verbose_name="收件地址")
    phone = models.CharField(max_length=11,verbose_name="联系电话")
    is_default= models.BooleanField(default=False,verbose_name="是否为默认地址")

    objects = AddressManager()
    class Meta:
        db_table = 'df_address'
        verbose_name = "地址"
        verbose_name_plural = verbose_name





