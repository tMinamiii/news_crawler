# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AllNewsItems(scrapy.Item):
    token_items = scrapy.Field()
    original_news_items = scrapy.Field()


class TokenItems(scrapy.Item):
    tokens = scrapy.Field()


class OriginalNewsItems(scrapy.Item):
    category = scrapy.Field()
    title = scrapy.Field()
    manuscript_len = scrapy.Field()
    manuscript = scrapy.Field()
