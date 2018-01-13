import csv
import json
import os

from scraping import yahoonews as yahoonews


def fetch_news(rss_dic, time, filetype):
    chunk_dic = scrape(rss_dic, time)
    for k, v in chunk_dic.items():
        timestr = time.strftime('%Y-%m-%d')
        targetdir = './data/{0}/{1}'.format(filetype, k)
        if not os.path.isdir(targetdir):
            os.makedirs(targetdir)

        filename = '{0}/{1}_{2}.{3}'.format(targetdir, k, timestr, filetype)
        write_news_file(filename, v, filetype)


def scrape(rss_dic, time, oneline=False) -> list:
    scraper = yahoonews.YahooNewsScraper()
    chunk_dic = {}
    for url in rss_dic.values():
        result = scraper.scrape_news(url, sleep=1, date=time, oneline=oneline)
        for k, v in result.items():
            if k in chunk_dic:
                chunk_dic[k].extend(v)
            else:
                chunk_dic[k] = v
    return chunk_dic


def write_news_file(filename, chunks, filetype):
    if filetype == 'json':
        if not os.path.isfile(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([], f)

        # あまり賢いやり方ではないが、せいぜい数回なのでこのやり方で我慢
        with open(filename, 'r', encoding='utf-8') as f:
            feeds = json.load(f)

        with open(filename, 'w', encoding='utf-8') as f:
            feeds.extend(chunks)
            json.dump(feeds, f, ensure_ascii=False)

    elif filetype == 'csv':
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f,  lineterminator='\n')
            for chunk in chunks:
                writer.writerow([chunk['category'], chunk['title'],
                                 chunk['manuscript_len'], chunk['manuscript']])


def main(filetype, time):
    rss = yahoonews.YahooRSSScraper()

    jp = rss.scrape_jp_newslist()
    world = rss.scrape_world_newslist()
    economic = rss.scrape_economic_newslist()
    sports = rss.scrape_sports_newslist()
    it_science = rss.scrape_it_science_newslist()
    life = rss.scrape_life_newslist()
    entertaiment = rss.scrape_entertaiment_newslist()

    fetch_news(jp, time, filetype)
    fetch_news(world, time, filetype)
    fetch_news(economic, time, filetype)
    fetch_news(sports, time, filetype)
    fetch_news(it_science, time, filetype)
    fetch_news(life, time, filetype)
    fetch_news(entertaiment, time, filetype)
