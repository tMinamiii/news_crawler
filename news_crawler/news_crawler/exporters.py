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


class SpiderSlot(object):
    def __init__(self, file, exporter, storage, uri, exporting):
        self.file = file
        self.exporter = exporter
        self.storage = storage
        self.uri = uri
        self.itemcount = 0
        self.exporting = exporting


def store_all_slots(slots):
    for category, slot in slots.items():
        slot.storage.store(slot.file)


class FeedExporter(feedexport.FeedExporter):

    def __init__(self, settings):
        super().__init__(settings)
        self.slot_cache = {}
        '''
        self.settings = settings
        self.urifmt = settings['FEED_URI']
        if not self.urifmt:
            raise NotConfigured
        self.format = settings['FEED_FORMAT'].lower()
        self.export_encoding = settings['FEED_EXPORT_ENCODING']
        self.storages = self._load_components('FEED_STORAGES')
        self.exporters = self._load_components('FEED_EXPORTERS')
        if not self._storage_supported(self.urifmt):
            raise NotConfigured
        if not self._exporter_supported(self.format):
            raise NotConfigured
        self.store_empty = settings.getbool('FEED_STORE_EMPTY')
        self._exporting = False
        self.export_fields = settings.getlist('FEED_EXPORT_FIELDS') or None
        self.indent = None
        if settings.get('FEED_EXPORT_INDENT') is not None:
            self.indent = settings.getint('FEED_EXPORT_INDENT')
        uripar = settings['FEED_URI_PARAMS']
        self._uripar = load_object(uripar) if uripar else lambda x, y: None
        '''

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        slot = self.slot
        uri_list = set()
        total_itemcount = 0
        for slot in self.slot_cache.items():
            if not slot.itemcount and not self.store_empty:
                return
            if self._exporting:
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
        category = item['category']
        if category not in self.slot_cache:

            uri = self.urifmt % {'category': category,
                                 'starttime': spider.starttime}

            storage = self._get_storage(uri)
            file = storage.open(spider)
            exporter = self._get_exporter(file,
                                          fields_to_export=self.export_fields,
                                          encoding=self.export_encoding,
                                          indent=self.indent)
            if self.store_empty:
                exporter.start_exporting()
                self._exporting = True

            self.slot_cache[category] = SpiderSlot(
                file, exporter, storage, uri, False)

        slot = self.slot_cache[category]
        if not slot.exporting:
            slot.exporter.start_exporting()
            slot.exporting = True
        slot.exporter.export_item(item)
        slot.itemcount += 1
        return item
