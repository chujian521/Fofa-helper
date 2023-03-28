#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# @Time    : 2023/03/28 20:22:09
# @Author  : chujian521
# @File    : fofa.py

import base64
import os
import time
import config
import argparse
import re
import requests
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from utils import fofa_useragent
from utils.levelData import LevelData
from utils.outputData import OutputData
from lxml import etree
from utils.tools import check_url_valid, searchkey_to_filename
from utils.logger import get_logger

logger = get_logger(name="fofa")

class Fofa:
    def __init__(self):
        self.headers_use = ""
        self.level = 0
        self.host_set = set()
        self.timestamp_set = set()
        self.oldLength = -1
        self.endcount=0
        self.filename = ""

        logger.info('''
 ____    _____   ____    ______     
/\  _`\ /\  __`\/\  _`\ /\  _  \    
\ \ \L\_\ \ \/\ \ \ \L\_\ \ \L\ \   
 \ \  _\/\ \ \ \ \ \  _\/\ \  __ \  
  \ \ \/  \ \ \_\ \ \ \/  \ \ \/\ \ 
   \ \_\   \ \_____\ \_\   \ \_\ \_\\
    \/_/    \/_____/\/_/    \/_/\/_/
 __  __          ___                            
/\ \/\ \        /\_ \                           
\ \ \_\ \     __\//\ \    _____      __   _ __  
 \ \  _  \  /'__`\\ \ \  /\ '__`\  /'__`\/\`'__\\
  \ \ \ \ \/\  __/ \_\ \_\ \ \L\ \/\  __/\ \ \/ 
   \ \_\ \_\ \____\/\____\\ \ ,__/\ \____\\ \_\ 
    \/_/\/_/\/____/\/____/ \ \ \/  \/____/ \/_/ 
                            \ \_\               
                             \/_/               V{}                                    
                                    
        '''.format(config.VERSION_NUM))

    def headers(self,cookie):
        headers_use = {
            'User-Agent': fofa_useragent.getFakeUserAgent(),
            'Accept': 'application/json, text/plain, */*',
            "cookie": cookie.encode("utf-8").decode("latin1")
        }
        return headers_use

    def logoutInitMsg(self):
        logger.info('''
            [*] LEVEL = {} , 初始化成功
            [*] 爬取延时: {}s
            [*] 爬取关键字: {}
            [*] 爬取结束数量: {}
            [*] 是否FUZZ: {}
            [*] 输出格式为: {}
            [*] 是否检查url: {}
            [*] 存储文件名: {}'''.format(self.level,self.timeSleep,self.searchKey,self.endcount,self.fuzz,self.output,self.check_url,self.filename)
                    )
        return

    def initKeyWord(self,keyword):
        tempkey=keyword.replace("'",'"')
        if '"' not in tempkey and ' ' not in tempkey:
            tempkey='"{}"'.format(tempkey)
        return tempkey

    def init(self):
        parser = argparse.ArgumentParser(description='Fofa-helper v{} 使用说明'.format(config.VERSION_NUM))
        parser.add_argument('--timesleep', '-t', help='爬取每一页等待秒数,防止IP被Ban,默认为3',default=3)
        parser.add_argument('--timeout', '-to', help='爬取每一页的超时时间',default=10)
        parser.add_argument('--keyword', '-k', help='fofa搜索关键字', required=True)
        parser.add_argument('--endcount', '-e', help='爬取结束数量')
        parser.add_argument('--level', '-l', help='爬取等级: 1-3 ,数字越大内容越详细,默认为 1')
        parser.add_argument('--output', '-o', help='输出格式:txt、json,默认为txt')
        parser.add_argument('--fuzz', '-f', help='关键字fuzz参数,增加内容获取粒度',action='store_true')
        parser.add_argument('--savepath', '-sp', help='保存结果的路径，默认为当前文件夹下的result目录',default="result")
        parser.add_argument('--savename', '-sn', help='保存结果的文件名称',default="")
        parser.add_argument('--checkurl', '-ck', help='是否检查url有效性，默认为False', default=False)
        args = parser.parse_args()
        self.timeSleep= int(args.timesleep)
        self.timeout = int(args.timeout)
        self.searchKey=self.initKeyWord(args.keyword)
        if args.endcount:
            self.endcount=int(args.endcount)
        else:
            self.endcount=100
        self.level=args.level if args.level else "1"
        self.levelData=LevelData(self.level)
        self.fuzz=args.fuzz
        self.check_url = args.checkurl
        self.output = args.output if args.output else "txt"
        self.savepath = args.savepath
        if not os.path.exists(self.savepath):
            os.makedirs(self.savepath)
        if not self.savepath.endswith(os.path.sep):
            self.savepath += os.path.sep
        self.filename = args.savename
        if not self.filename:
            self.filename = "{}_{}.{}".format(self.savepath+searchkey_to_filename(self.searchKey), time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time())), self.output)
        else:
            self.filename = self.savepath + self.filename + "." + self.output
        self.outputData = OutputData(self.filename, pattern=self.output)
        self.logoutInitMsg()

    def get_count_num(self, search_key):
        """
        获取关键字的搜索数量值
        :param search_key:
        :return:
        """
        headers_use = fofa_useragent.getFofaPageNumHeaders()
        searchbs64 = base64.b64encode(f'{search_key}'.encode()).decode()
        logger.info("[*] 爬取页面为:https://fofa.info/result?qbase64=" + searchbs64)
        html = requests.get(url="https://fofa.info/result?qbase64=" + searchbs64, headers=headers_use, timeout=self.timeout).text
        tree = etree.HTML(html)
        try:
            countnum = tree.xpath('//span[@class="hsxa-highlight-color"]/text()')[0]
            # standaloneIpNum = tree.xpath('//span[@class="hsxa-highlight-color"]/text()')[1]
        except Exception as e:
            logger.error("[-] error:{}".format(e))
            countnum = '0'
            pass
        logger.info("[*] 存在数量:" + countnum)
        # print("[*] 独立IP数量:" + standaloneIpNum)
        return searchbs64

    def getTimeList(self, text):
        """
        获取时间列表
        :param text:
        :return:
        """
        timelist = list()
        pattern = "<span>[0-9]*-[0-9]*-[0-9]*</span>"
        result = re.findall(pattern, text)
        for temp in result:
            timelist.append(temp.replace("<span>", "").replace("</span>", "").strip())
        return timelist

    def fofa_spider_page(self, searchbs64):
        """
        获取一页的数据
        :rtype: object
        """
        TEMP_RETRY_NUM=0

        while TEMP_RETRY_NUM < config.MAX_MATCH_RETRY_NUM:
            try:
                request_url = 'https://fofa.info/result?qbase64=' + searchbs64 + "&full=false&page_size=10"
                # print(f'request_url:{request_url}')
                rep = requests.get(request_url, headers=self.headers_use, timeout=self.timeout)
                self.levelData.startSpider(rep)

                # tree = etree.HTML(rep.text)
                # urllist = tree.xpath('//span[@class="hsxa-host"]/a/@href')
                timelist = self.getTimeList(rep.text)
                logger.info("[*] 已爬取条数 [{}]: ".format(len(self.host_set))+str(self.levelData.formatData))

                for url in self.levelData.formatData:
                    self.host_set.add(url)
                    if self.check_url:
                        if not check_url_valid(url):
                            logger.warning("[-] " + url + " 无法访问！")
                            continue
                    with open(self.filename, 'a+', encoding="utf-8") as f:
                        f.write(str(url) + "\n")
                for temptime in timelist:
                    self.timestamp_set.add(temptime)
                time.sleep(self.timeSleep)
                return
            except Exception as e:
                logger.error("[-] error:{}".format(e))
                TEMP_RETRY_NUM+=1
                logger.info('[-] 第{}次尝试获取页面URL'.format(TEMP_RETRY_NUM))
                pass


        logger.error('[-] FOFA资源获取重试超过最大次数,程序退出')
        exit(0)


    def fofa_common_spider(self, search_key, searchbs64):
        while len(self.host_set) < self.endcount and self.oldLength !=len(self.host_set):
            self.oldLength=len(self.host_set)
            self.timestamp_set.clear()
            self.fofa_spider_page(searchbs64)
            search_key_modify= self.modify_search_time_url(search_key)
            # print(search_key_modify)
            searchbs64_modify = quote_plus(base64.b64encode(search_key_modify.encode()))
            search_key = search_key_modify
            searchbs64 = searchbs64_modify
        if len(self.host_set) >= self.endcount:
            logger.info("[*] 数据爬取结束")
            return
        if self.oldLength == len(self.host_set):
            logger.info("[-] 数据无新增,退出爬取")
            return

    def fofa_fuzz_spider(self, search_key, searchbs64):
        while len(self.host_set) < self.endcount and self.oldLength !=len(self.host_set):
            self.oldLength=len(self.host_set)
            self.timestamp_set.clear()
            self.fofa_spider_page(searchbs64)
            search_key_modify = self.modify_search_time_url(search_key)

            searchbs64_modify = quote_plus(base64.b64encode(search_key_modify.encode()))
            search_key = search_key_modify
            searchbs64 = searchbs64_modify
        if len(self.host_set) >= self.endcount:
            logger.info("[*] 数据爬取结束")
            return
        if self.oldLength == len(self.host_set):
            logger.info("[-] 数据无新增,退出爬取")
            return

    def modify_search_time_url(self, search_key):
        """
        根据时间修订搜索值
        :param search_key:
        :return:
        """
        
        # get before_time in search_key.
        # if there is no before_time, set tomorrow_time as default
        before_time_in_search_key = (datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d')
        if "before=" in search_key:
            pattern = r'before="([^"]+)"'
            match = re.search(pattern, search_key)
            before_time_in_search_key = match.group(1)
        time_before_time_in_search_key = datetime.strptime(before_time_in_search_key, "%Y-%m-%d").date()
        
        # regard the_earliest_time.tomorrow as optimized time_before
        timestamp_list=list(self.timestamp_set)
        timestamp_list.sort()

        time_first = timestamp_list[0].split(' ')[0].strip('\n').strip()
        time_first_time = datetime.strptime(time_first, "%Y-%m-%d").date()
        time_before = time_first_time+timedelta(days=1)
        
        # check if optimized time_before can be used
        if time_before>=time_before_time_in_search_key:
            time_before = time_before_time_in_search_key - timedelta(days=1)
 
        #logger.info(time_before)

        if 'before' in search_key:
            logger.debug(search_key)
            search_key = search_key.split('&& before')[0]
            search_key = search_key.strip(' ')
            search_key = search_key + ' && ' + 'before="' + str(time_before) + '"'
        else:
            search_key = search_key + ' && ' + 'before="' + str(time_before) + '"'
        search_key_modify = search_key

        # print('[*] 搜索词： ' + search_key_modify)

        return search_key_modify

    def run(self):
        searchbs64 = self.get_count_num(self.searchKey)
        if not self.fuzz:
            self.fofa_common_spider(self.searchKey, searchbs64)
        else:
            self.fofa_fuzz_spider(self.searchKey, searchbs64)
        logger.info('[*] 抓取结束，共抓取数据 ' + str(len(self.host_set)) + ' 条\n')

    def main(self):
        self.init()
        logger.info('[*] 开始运行')
        self.run()

if __name__ == '__main__':
    fofa = Fofa()
    fofa.main()
