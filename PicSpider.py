import json
import re
from multiprocessing import Pool
from urllib.parse import urlencode

import os
from bs4 import BeautifulSoup
import requests
from hashlib import md5
from requests import RequestException
from config import *
import pymongo
from json.decoder import JSONDecodeError

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]




#请求索引页，提取页面内容
def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3
    }

    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code ==200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None


#解析索引页
def parse_page_index(html):
    #格式化数据为json格式，返回一个json类型对象
    try:
        datas = json.loads(html)
        # print(data.get('data')[10])
        if datas and 'data' in datas.keys():
            for item in datas.get('data'):
                #返回一个生成器对象
                yield item.get('article_url')
    except JSONDecodeError:
        return None



#请求详情页
def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code ==200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错',url)
        return None

#解析详情页的url
def parse_page_datail(html,url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    images_pattern = re.compile('gallery: JSON.parse\((.*?)\)\,',re.S)
    result = re.search(images_pattern, html)
    if result:
        data = json.loads(result.group(1))
        idata = re.sub(r'\\', '', data)
        #json类型的str转化为dict
        iidata = eval(idata)
        if iidata and 'sub_images' in iidata.keys():
            sub_images = iidata.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:download_iamge(image)
            return {
                'titel':title,
                'url':url,
                'images':images
            }
        # print(iidata)

#存储到MongoDB
def save_to_mongo(result):
    if db[MONGO_DB].insert(result):
        print('存储成功',result)
        return True
    return False

#下载图片到本地
def download_iamge(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code ==200:
            #图片返回二进制response.content
            save_images(response.content)
        return None
    except RequestException:
        print('下载出错',url)
        return None

#保存文件
def save_images(content):
    file_images = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_images):
        with open(file_images, 'wb') as f:
            f.write(content)
            f.close()



def main(offset):
    html = get_page_index(offset, KEYWORD)
    #遍历生成器对象，提取所有url
    for url in parse_page_index(html):
        # print(url)
        html = get_page_detail(url)
        # print(html)
        if html:
            result = parse_page_datail(html,url)
            if result:
                save_to_mongo(result)
            # print(result)



if __name__ == '__main__':
    pool = Pool()
    for x in range(GROUP_START, GROUP_END + 1):
        num = x * 20
    pool.map(main, num)