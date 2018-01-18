import datetime
import logging

import scrapy
from news_crawler.items import OriginalNewsItems
from news_crawler.items import AllNewsItems

logger = logging.getLogger(__name__)


class YahooNewsSpider(scrapy.Spider):
    name = "yahoonews"
    # allowed_domains = ['*.yahoo.co.jp']
    start_urls = ['https://headlines.yahoo.co.jp/rss/list']
    scraped_url = set()
    starttime = datetime.datetime.now()
    oneline = True

    def parse(self, response):
        news_areas = response.css('div.rss_listbox')
        for area in news_areas:
            if area.css('h3[id=news]'):
                major_items = area.css('div.ymuiHeaderBGLight > h4.ymuiTitle')
                containers = area.css('div.ymuiContainer')
                break
        for mi, con in zip(major_items, containers):
            major_item = mi.css('::text').extract_first()
            links = con.css('ul.ymuiList > li.ymuiArrow > dl')
            if self.settings['NEWS_MAJOR_ITEMS'] is not None:
                if major_item not in self.settings['NEWS_MAJOR_ITEMS']:
                    continue
            for link in links:
                # name = link.css('dt::text').extract_first()
                url = link.css('dd > a::attr(href)').extract_first()
                if url not in self.scraped_url:
                    self.scraped_url.add(url)
                    yield scrapy.Request(
                        response.urljoin(url), callback=self.parse_rss_xml)

    def parse_rss_xml(self, response):
        items = response.css('item')
        for item in items:
            pubdate_str = item.css('pubDate::text').extract_first()
            if self.is_old_news(pubdate_str, self.starttime) is True:
                # rssなのでbreakでもよいが念の為
                continue
            title = item.css('title::text').extract_first().strip()
            link = item.css('link::text').extract_first()
            category = item.css('category::text').extract_first()
            yield scrapy.Request(
                response.urljoin(link),
                callback=self.parse_manuscript,
                meta={'category': category,
                      'title': title})

    def parse_manuscript(self, response):

        paragraphs = response.css('div.paragraph')
        manuscript = ''
        for para in paragraphs:
            try:
                heading = para.css(
                    'div.ynDetailHeading > em::text').extract_first()
                if heading is not None:
                    manuscript += heading.strip()
                detail_text = para.css('p.ynDetailText::text')
                for text in detail_text:
                    manuscript += text.extract().strip()
            except Exception:
                logger.warn('Error occoured while scraping : ' + response.url)

        if self.oneline:
            manuscript = manuscript.replace('\r', '')
            manuscript = manuscript.replace('\n', '')
        original_news_items = OriginalNewsItems()
        original_news_items['manuscript'] = manuscript
        original_news_items['manuscript_len'] = len(manuscript)
        original_news_items['category'] = response.meta.get('category')
        original_news_items['title'] = response.meta.get('title')
        items = AllNewsItems()
        items['original_news_items'] = original_news_items
        yield items

    def is_old_news(self, pubdate_str: str, specified_date: datetime) -> bool:
        if specified_date is None:
            return False
        date_format = '%a, %d %b %Y %H:%M:%S %z'
        pubdate = datetime.datetime.strptime(pubdate_str, date_format)
        # 指定した日付より後のニュースは最新ニュースとして扱う
        # 指定した日付よりも前のニュースは古いのでTrue
        return pubdate.date() < specified_date.date()
