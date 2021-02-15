import re
import requests
import base64
import xxhash
import plistlib
from jsonpath import jsonpath
import struct
from lxml import etree
from Cryptodome.Cipher import ARC4
from plistlib import FMT_BINARY, _BinaryPlistParser, _undefined

# 拿到电影代号num
class getMovie_num():
    def __init__(self, name='你好，李焕英'):
        self.url = 'https://search.douban.com/movie/subject_search'
        self.cookies = None
        self.movie_name = name
        self.session = requests.Session()
        self.session.headers = {
            'Connection': 'close',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
            'Referer': 'https://movie.douban.com',


        }
        self.session.cookies = self.session.get(self.url).cookies
        self.DATA = None
        self.response = None

    def run(self):
        # self.session.proxies = {
        #     'http': 'http://49.71.141.170:28992',
        #     'https': 'https://49.71.141.170:28992'
        # }
        params = {
            'search_text': self.movie_name,
            'cat': 1002
        }
        response = self.session.get(self.url, params=params)
        text = self.js_decrypt(response)
        movie_num = self.get_movie_num(text)
        page_num = self.get_page_num(movie_num)
        return movie_num, page_num

    def js_decrypt(self, response): # 解密window.__DATA__，拿到首个电影的movie_num
        DATA = re.search('window.__DATA__ = "([^"]+)"', response.content.decode()).group(1)
        self.DATA = DATA
        t = base64.b64decode(DATA)
        s = max((len(t) - 2 * 16) // 3, 0)
        key = t[s:s + 16]
        data = t[0:s] + t[s + 16:]

        key = xxhash.xxh64_hexdigest(key, 41405).encode() # 转换为二进制。
        cipher = ARC4.new(key)  # 传入key，创建RC4对象
        text = cipher.decrypt(data) # 解密

        text = plistlib.loads(text, fmt=FMT_BINARY) # 解析数据
        return text

    def get_movie_num(self, text):
        # 将json字典转为字符串，然后用正则找数据。
        temp = [i for i in jsonpath(text, '$..k') if self.movie_name in str(i)]
        movie_num = re.findall(r"subject_id:\\'(\d*)", str(temp))[0]
        return movie_num

    def get_page_num(self, movie_num):
        url = "https://movie.douban.com/subject/" + movie_num
        content = self.session.get(url).content.decode()
        page_num = re.search(' ([\d]*)',etree.HTML(content).xpath("//div[1]/h2/span/a/text()")[0]).group(1)
        return page_num




# 猴子补丁——复制plist.py的源码，修改，覆盖_BinaryPlistParser对象的_read_object方法。
def _read_object(self, ref):
    result = self._objects[ref]
    if result is not _undefined:
        return result

    offset = self._object_offsets[ref]
    self._fp.seek(offset)
    token = self._fp.read(1)[0]
    tokenH, tokenL = token & 0xF0, token & 0x0F

    if token == 0x00:
        result = None

    elif token == 0x08:
        result = False

    elif token == 0x09:
        result = True

    elif token == 0x0f:
        result = b''

    elif tokenH == 0x10:  # int
        result = int.from_bytes(self._fp.read(1 << tokenL),
                                'big', signed=tokenL >= 3)

    elif token == 0x22:  # real
        result = struct.unpack('>f', self._fp.read(4))[0]

    elif token == 0x23:  # real
        result = struct.unpack('>d', self._fp.read(8))[0]

    elif tokenH == 0x40:  # ascii string
        s = self._get_size(tokenL)
        result = self._fp.read(s).decode('ascii')
        result = result

    elif tokenH == 0x50:  # unicode string
        s = self._get_size(tokenL)
        result = self._fp.read(s * 2).decode('utf-16be')

    elif tokenH == 0xA0:  # array
        s = self._get_size(tokenL)
        obj_refs = self._read_refs(s)
        result = []
        self._objects[ref] = result
        result.extend(self._read_object(x) for x in obj_refs)

    elif tokenH == 0xD0:  # dict
        s = self._get_size(tokenL)
        key_refs = self._read_refs(s)
        obj_refs = self._read_refs(s)
        result = self._dict_type()
        self._objects[ref] = result
        for k, o in zip(key_refs, obj_refs):
            result[self._read_object(k)] = self._read_object(o)

    self._objects[ref] = result
    return result
# 猴子补丁，重写plistlib.py的_read_object方法。
_BinaryPlistParser._read_object = _read_object


def next_page(subject_id):
    page = 0
    while True:
        yield "https://movie.douban.com/subject/" + subject_id + "/comments?start=" + str(20 * page) + "&limit=20&status=P&sort=new_score&comments_only=1"
        page += 1


def pull_data(nptor):
    response = li.session.get(next(nptor))
    while response.status_code == 200:
        data = []
        content = response.content.decode("unicode_escape")
        for i in etree.HTML(content).xpath("//div/div[2]/p/span/text()"):
            data.append(i)
        response = li.session.get(next(nptor))
        yield data

if __name__ == '__main__':
    # getMovie_num("拆弹专家2")
    li = getMovie_num("温暖的抱抱")
    n, p = li.run() # 返回subject_id,  电影总页数
    data = []
    nptor = next_page(n)
    for i in pull_data(nptor):
        data.append(i)



