# daily_news_scraper

Raspberry Pi 3 Model B上でscrapy + scrapyd を使用してYahooニュースをクローリングします。

## 動作環境

- OS: Raspbian (Debian系)
- CPU: ARMv8 1.2GHz Quad Core
- Memory: 1G Byte

## 自宅環境

- FTP server address : olive.local
    - ニュースの置き場
- Port : 46800

## 概要

1. cronで毎日20時にクローラージョブを開始
2. [Yahoo!ニュース](https://headlines.yahoo.co.jp/rss/list)のRSS一覧サイトをスクレイピング
3. ニュースという大項目のRSS xmlのURLを取得
4. xmlから本日と同じ日付のニュースのURLを取得
5. 各ニュースの「カテゴリー」、「タイトル」、「原稿の長さ」、「原稿本文」をスクレイピング
6. CSV形式で自宅のFTPサーバーに保存

## 設定

### settings.py

`FEED_URI`を変更することで別の環境でも動作すると思います(未検証)
(デフォルトのFEED_URIは自宅のFTPサーバーになっています。)

### news_crawler/scrapy.cfg,

- project名は`news_crawler`です
- urlは、`localhost:46800`となっています

### ./scrapyd.conf

- こちらでもポートは`46800`に設定されています
- IPアドレスは`0.0.0.0`にバインドされています

### cron.conf

scrapydはcurlコマンドで登録したクローラーを開始できるので
cronで毎日20時に実行してクローラージョブを開始しています

```
0 20 * * * curl http://localhost:46800/schedule.json -d project=news_crawler -d spider=yahoonews
```
