from django.core.files.storage import Storage

from fdfs_client.client import Fdfs_client

class FDFSStorage(Storage):
    def _open(self,name,mode='rb'):
        pass

    def _save(self,name,content):
        '''保存文件'''
        #创建Fdfs_client 对象
        client= Fdfs_client(conf_path='./utils/fdfs/client.conf')
        res = client.upload_appender_by_buffer(content.read())
        # print(res.get('Status'))
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FAST dfs失败')

        filename = res.get('Remote file_id')
        return filename

    def exists(self,name):
        return False

    def url(self, name):
        return 'http://192.168.107.132:8888/'+name
