# -*- coding: utf-8 -*-

import re
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import MeCab

import mojimoji
import settings
from news_crawler.items import TokenItems


class YahooNewsTokenizer:
    def __init__(self):
        self._m = MeCab.Tagger(settings.MECAB_DICTIONARY)
        # compileしておく
        self.eng_sentences = re.compile(r'[a-zA-Z0-9]+[ ,\.\'\:\;\-\+?\!]')
        self.numbers = re.compile(r'[0-9０-９]+')
        self.symbols1 = re.compile(r'[\!\?\#\$\%\&\'\*\+\-\.\^_\`\|\~\:]+')
        self.symbols2 = re.compile(r'[\<\=\>\;\{\}\[\]\`\@\(\)\,\\]+')
        self.cjk_symbols = re.compile(r'[“└┐（）【】『』｛｝「」［］《》〈〉！？＝]+')

    def sanitize(self, manu: str) -> str:
        # 英文を取り除く（日本語の中の英字はそのまま）
        manu = re.sub(self.eng_sentences, '', manu)
        # 記号や数字は「 」に変換する。
        # (単純に消してしまうと意味不明な長文になりjanomeがエラーを起こす)
        manu = re.sub(self.numbers, '0', manu)
        manu = re.sub(self.symbols1, ' ', manu)
        manu = re.sub(self.symbols2, ' ', manu)
        manu = re.sub(self.cjk_symbols, ' ', manu)
        return manu

    def tokenize(self, manuscript: str) -> list:
        token_list = []
        append = token_list.append
        try:
            tokens = self._m.parse(manuscript).split('\n')
        except IndexError:
            print(manuscript)
            return None
        for tok in tokens:
            # 表層形\t品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用形,活用型,原形,読み,発音
            tok = re.split(r'[\,\t]', tok)
            if len(tok) < 10:
                continue
            ps = tok[1]
            if ps not in ['名詞', '動詞', '形容詞']:
                continue
            # 原形があれば原形をリストに入れる
            w = tok[7]
            if w == '*' or w == '':
                # 原形がなければ表層系(原稿の単語そのまま)をリストに入れる
                w = tok[0]
            if w == '' or w == '\n':
                continue
            # 全角英数はすべて半角英数にする
            w = mojimoji.zen_to_han(w, kana=False, digit=False)
            # 半角カタカナはすべて全角にする
            w = mojimoji.han_to_zen(w, digit=False, ascii=False)
            # 英語はすべて小文字にする
            w = w.lower()
            append(w)
        return token_list


class NewsCrawlerPipeline(object):

    def process_item(self, item, spider):
        manuscript = item['manuscript']
        tokenizer = YahooNewsTokenizer()
        sanitized = tokenizer.sanitize(manuscript)
        tokens = tokenizer.tokenize(sanitized)
        token_items = TokenItems()
        token_items['tokens'] = tokens
        item.token_items = token_items
        return item
