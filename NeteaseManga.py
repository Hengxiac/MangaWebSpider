#coding UTF-8
import urllib.request
import re,os,zlib,time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver


class NetEase:
    def __init__(self, url):
        self.base_url = "https://manhua.163.com/"
        self.url = url
        
        content = self.get_content(self.url)
        if not content:
            print ("该漫画不存在!")
            return

        self.title = self.get_title(content)
        self.current_title = self.title
        self.driver = 0
        self.volume_url_arr = self.get_volume_url_arr(url)
        self.current_volume = ''
        # 标记每次下载图片时,是否先检查本地已存在对应图片
        self.need_check_pic = False


    def get_content(self, url):
        #打开网页
        try:
            response = urllib.request.urlopen(url,timeout = 20)
            html = response.read().decode("utf-8")
            return html
        except Exception as e:
            print (e)
            print ("打开网页："+ url + "失败。")
            return None

    def get_title(self, content):
        pattern = re.compile('class="f-toe sr-detail__heading">(.*?)</h1>',re.S)
        result = re.search(pattern, content)
        title_list = result.groups(1)
        if(title_list[0]):
            title = title_list[0]
            return title
        else:
            print("标题获取失败")
            return None
    
    def get_volume_url_arr(self, url):
        self.driver = webdriver.PhantomJS()
        self.driver.get(url)
        self.driver.find_element_by_class_name('j-load-more-button').click()
        time.sleep(0.3)

        pattern = re.compile('class="sr-catalog__bd f-cb js-catalog-body">(.*?)class="m-gift sr-gift"',re.S)
        result = re.search(pattern, self.driver.page_source)
        volume_list = result.groups(1)

        pattern2 = re.compile('class="f-toe".*?title="(.*?)".*?>.*?</a>',re.S)
        pattern = re.compile('class="f-toe".*?href="(.*?)".*?>.*?</a>',re.S)
        volumes = re.findall(pattern, volume_list[0])
        volumenames = re.findall(pattern2, volume_list[0])
        arr = []

        for volumename in volumenames:           
            arr.append(volumename.replace('&nbsp;',' '))
        for volume in volumes:
            volume_url = self.base_url + volume
            arr.append(volume_url)
        
        self.driver.quit()
        return arr
    
    def get_pic_urls(self,pageurl):
        
        self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(1136, 768) # 设置浏览器窗口大小
        self.driver.get(pageurl)

        time.sleep(2)
        WebDriverWait(self.driver,5).until(EC.presence_of_element_located((By.CSS_SELECTOR,'div.panel-btn-showbar')))
        self.driver.find_element_by_css_selector('div.panel-btn-showbar').click()
        
        WebDriverWait(self.driver,3).until(EC.presence_of_element_located((By.CSS_SELECTOR,'div.js-setting')))
        #打开下方菜单栏
        #选择模式双页，从左阅读,左右翻页
        self.driver.find_element_by_css_selector('div.js-setting').click();
        time.sleep(0.1)
        self.driver.find_element_by_css_selector('div.js-mixed').click()
        self.driver.find_element_by_css_selector('div.js-h').click()
        self.driver.find_element_by_css_selector('div.js-l2r').click()

        total_page_for_this_volume = int(self.driver.find_element_by_css_selector('span.js-totalIndex').text)
        current_page_index = 1
        page_arr = []
        WebDriverWait(self.driver,5).until(EC.presence_of_all_elements_located((By.CLASS_NAME,'img-box')))

        for current_page_index in range(1, total_page_for_this_volume + 1):
            #pageurls = self.driver.find_elements_by_xpath('//div[@class="img-box-wrapper"]/div/img')
            time.sleep(1.5)
            #self.driver.get_screenshot_as_file(str(current_page_index)+'.jpg')
            WebDriverWait(self.driver,5).until(EC.presence_of_all_elements_located((By.XPATH,'//div[@class="img-box-wrapper"]/div/img')))
            divs = self.driver.find_elements_by_xpath('//div[@class="img-box-wrapper"]/div')

            for pageurl in divs:
                try:
                    page_class = pageurl.get_attribute('class')
                    if page_class == 'img-box img-box-leftin' or page_class == 'img-box img-box-rightin':
                        page_url = pageurl.find_element_by_tag_name('img')
                        if page_url:
                            img = page_url.get_attribute('src')
                            page_arr.append(img)
                except Exception as e:
                    print('本图片未找到。')
                    print(e)
       
            self.driver.find_element_by_css_selector('.js-pager').click()
            if current_page_index < total_page_for_this_volume:
                WebDriverWait(self.driver,5).until(EC.presence_of_element_located((By.XPATH,'//div[@data-index="'+str(current_page_index + 1) +'"]')))
                try:
                    next_page = self.driver.find_element_by_xpath('//div[@data-index="'+str(current_page_index + 1) +'"]')
                    next_page.click()
                except Exception as e:
                    print(e)

            current_page_index += 1
            
        
        self.driver.quit()
        return page_arr

    def save_pic(self,path, title , volume_allpage_urls):
        dir_path = path + '/' + title
        self.create_dir_path(dir_path)

        # 判断是否已经下载过
        list = os.listdir(dir_path)
        if len(list) >= len(volume_allpage_urls):
            print(title + "已经下载过了.")
            return
     

        # 获取图片时会偶尔出现请求超时的情况,会导致一部漫画存在部分缺失,此时文件夹中已存在大部分图片
        # 当前已存在图片大于一定数量时判定为存在少数缺页情况,这时候通过判断只对未存在图片进行请求
        if len(list) >= (len(volume_allpage_urls) / 2):
            print("每章图片下载前先检查本地是否已经存在")
            self.need_check_pic = True

        for i in range(0, len(volume_allpage_urls)):
            picurl = volume_allpage_urls[i]
            if picurl == None:
                continue

            pic_path = dir_path + '/' + str(i+1) +'.jpg'
            if self.need_check_pic:
                exists = os.path.exists(pic_path)
                if exists:
                    print ("图片已经存在")
                    continue
            
            opener = urllib.request.build_opener()
            
            headers = [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'),
                ('Referer', self.current_volume)
            ]
            opener.addheaders = headers
            urllib.request.install_opener(opener)

            connection_tries = 1
            for connection_tries in range(1, 11):
                try:
                    urllib.request.urlretrieve(picurl,pic_path)
                    break
                except Exception as e:
                    if connection_tries <= 10:
                        connection_tries += 1
                        continue
                    else:
                        print('无法连接服务器，下载「'+ title + '」失败')
                        break
        if  connection_tries <= 10:
            print (title + "成功下载完成！")

    def save_all_volumes(self,path):
        volume_path = path + '/' + self.title
        self.create_dir_path(volume_path)

        volumenum = (len(self.volume_url_arr) + 1) // 2
        title_arr = self.volume_url_arr[ : volumenum]
        url_arr   = self.volume_url_arr[volumenum : ]
        for i in range(0, volumenum):
            self.current_title = title_arr[i]
            volume_allpage_urls = self.get_pic_urls(url_arr[i])
            self.current_volume = url_arr[i]
            self.save_pic(volume_path, title_arr[i], volume_allpage_urls)
        
        print("全部任务已下载完成！")
        self.driver.quit()

    def save_one_volume(self,path, volume_number):
        volume_path = path + '/' + self.title
        self.create_dir_path(volume_path)

        volumenum = (len(self.volume_url_arr) +1) // 2
        title_arr = self.volume_url_arr[ : volumenum]
        url_arr   = self.volume_url_arr[volumenum : ]
        if volume_number > volumenum or volume_number < 1:
            print("该卷（话）不存在！")
            return
        
        volume_allpage_urls = self.get_pic_urls(url_arr[volume_number-1])
        self.current_volume = url_arr[volume_number - 1]
        self.current_title = title_arr[volume_number -1]
        self.save_pic(volume_path, title_arr[volume_number-1], volume_allpage_urls)


    def save_volumes_by_range(self,path, volume_number_start, volume_number_end):
        volume_path = path + '/' + self.title
        self.create_dir_path(volume_path)

        volumenum = (len(self.volume_url_arr) +1) // 2
        title_arr = self.volume_url_arr[ : volumenum]
        url_arr   = self.volume_url_arr[volumenum : ]
        
        #防止输入范围错误 
        # 1.开始卷大于终止卷
        if volume_number_start > volume_number_end:
            temp = volume_number_start
            volume_number_start = volume_number_end
            volume_number_end = temp
        #2.最小从第一卷开始
        if volume_number_start < 1:
            volume_number_start = 1
        #3.最多到最后一卷
        if volume_number_end > volumenum:
            volume_number_end = volumenum                 
        for i in range(volume_number_start-1, volume_number_end):
            self.current_title = title_arr[i]
            volume_allpage_urls = self.get_pic_urls(url_arr[i])
            self.current_volume = url_arr[i]
            self.save_pic(volume_path, title_arr[i], volume_allpage_urls)

        print("全部任务已下载完成！")

    def create_dir_path(self, path):
        #以漫画名创建文件夹
        exists = os.path.exists(path)
        if not exists:
            print("创建文件夹 : " + self.current_title)    
            os.makedirs(path)
        else:
            print("文件夹 : " + self.current_title +"已存在!")


save_path = "E:/python/netease"
url = 'https://manhua.163.com/source/4458002705630123103'
netease = NetEase(url)
netease.save_one_volume(save_path,1)
