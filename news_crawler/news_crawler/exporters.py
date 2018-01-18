import logging
import posixpath
from ftplib import FTP

from scrapy.extensions import feedexport
from scrapy.utils.ftp import ftp_makedirs_cwd
from scrapy.utils.log import failure_to_exc_info
from twisted.internet import defer

from six.moves.urllib.parse import urlparse

logger = logging.getLogger(__name__)


class FTPFeedStorage(feedexport.BlockingFeedStorage):

    def __init__(self, uri):
        u = urlparse(uri)
        self.host = u.hostname
        self.port = int(u.port or '21')
        self.username = u.username
        self.password = u.password
        self.path = u.path

    def _store_in_thread(self, file):
        file.seek(0)
        ftp = FTP()
        ftp.encoding = 'utf-8'
        ftp.connect(self.host, self.port)
        ftp.login(self.username, self.password)
        dirname, filename = posixpath.split(self.path)
        ftp_makedirs_cwd(ftp, dirname)
        ftp.storbinary('STOR %s' % filename, file)
        ftp.quit()


class MySpiderSlot(object):
    def __init__(self, 
                 csv_file, csv_exporter, csv_storage, csv_uri
                 token_file, token_exporter, token_storage, token_uri):
        self.csv_file = csv_file
        self.csv_exporter = csv_exporter
        self.csv_storage = csv_storage
        self.csv_uri = csv_uri
        self.token_file = token_file
        self.token_exporter = token_exporter
        self.token_storage = token_storage
        self.token_uri = token_uri
        self.itemcount = 0
        self.exporting = False

def store_all_slots(slots):
    for _, slot in slots.items():
        slot.storage.store(slot.file)


class FeedExporter(feedexport.FeedExporter):

    def __init__(self, settings):
        super().__init__(settings)
        self.slot_cache = {}

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        uri_list = set()
        total_itemcount = 0
        for _, slot in self.slot_cache.items():
            if not slot.itemcount and not self.store_empty:
                return
            if slot.exporting:
                slot.exporter.finish_exporting()
                slot.exporting = False
            total_itemcount += slot.itemcount
            uri_list.add(slot.uri)
        logfmt = "%s %%(format)s feed (%%(itemcount)d items) in: %%(uri)s"
        log_args = {'format': self.format,
                    'itemcount': total_itemcount,
                    'uri': uri_list}
        d = defer.maybeDeferred(store_all_slots, self.slot_cache)
        d.addCallback(lambda _: logger.info(logfmt % "Stored", log_args,
                                            extra={'spider': spider}))
        d.addErrback(lambda f: logger.error(logfmt % "Error storing", log_args,
                                            exc_info=failure_to_exc_info(f),
                                            extra={'spider': spider}))
        return d

    def item_scraped(self, item, spider):
        category = item.original_news_items['category']
        if category not in self.slot_cache:
            timestr = spider.starttime.strftime('%Y-%m-%d')
            csv_uri = self.urifmt % {'ftpuser': self.settings.FTP_USER,
                                     'ftppass': self.settgins.FTP_PASS,
                                     'ftpaddress': self.setting.FTP_ADDRESS,
                                     'targetdir': self.setting.FTP_NEWS_DIR,
                                     'category': category,
                                     'starttime': timestr,
                                     'format': self.settings.FEED_FORMAT}
            token_uri = self.urifmt % {'ftpuser': self.settings.FTP_USER,
                                       'ftppass': self.settgins.FTP_PASS,
                                       'ftpaddress': self.setting.FTP_ADDRESS,
                                       'targetdir': self.setting.FTP_TOKEN_DIR,
                                       'category': category,
                                     'starttime': timestr,
                                     'format': self.settings.FEED_FORMAT}
            
            csv_storage = self._get_storage(csv_uri)
            token_storage = self._get_storage(token_uri)
            csv_file = csv_storage.open(spider)
            token_file = token_storage.open(spider)

            csv_exporter = self._get_exporter(csv_file,
                                          fields_to_export=self.export_fields,
                                          encoding=self.export_encoding,
                                          indent=self.indent)
            token_exporter = self._get_exporter(token_file,
                                          fields_to_export=self.export_fields,
                                          encoding=self.export_encoding,
                                          indent=self.indent)
            self.slot_cache[category] = MySpiderSlot(
                csv_file, csv_exporter, csv_storage, csv_uri,
                token_file, token_exporter, token_storage, token_uri)

        slot = self.slot_cache[category]
        if self.store_empty:
                exporter.start_exporting()
                slot.exporting = True

        if not slot.exporting:
            slot.csv_exporter.start_exporting()
            slot.token_exporter.start_exporting()
            slot.exporting = True
        slot.csv_exporter.export_item(item.original_news_items)
        slot.token_exporter.export_item(item.token_items)
        slot.itemcount += 1
        return item
