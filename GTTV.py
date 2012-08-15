#!/usr/bin/env python3


# TODO: Use flvstreamer?
# TODO: Use DLL library.
# TODO: Miro extension?
# TODO: Opera extension?
# TODO: Don't hardcode the media XML namespace.


# Standard:
import email, subprocess, sys, urllib.parse, urllib.request

# External:
import chardet, fixes, lxml.etree, lxml.html, unipath


class Url:
    __PARSERS_BY_TYPE = {
        'html': lxml.html.fromstring,
        'xml': lxml.etree.fromstring,
    }
    
    
    @classmethod
    def convert_query_to_string(class_, query):
        encoded_query = []
        
        for key, values in query.items():
            for value in (values if isinstance(values, list) else [values]):
                if not isinstance(value, str) and not isinstance(value, bytes):
                    value = str(value)
                
                encoded_query.append('%s=%s' % (
                    urllib.parse.quote(key, safe = b'[]'),
                    urllib.parse.quote(value, safe = b'[]')))
        
        return '&'.join(encoded_query)
    
    
    def __init__(self, url, query = None):
        if isinstance(url, Url):
            self.__components = url.__components
        else:
            self.__components = urllib.parse.urlparse(url)
        
        if query is not None:
            self.query = query
    
    
    @property
    def host_name(self):
        return self.__components.hostname
    
    
    @host_name.setter
    def host_name(self, host_name):
        components = self.__components._asdict()
        components['netloc'] = host_name
        
        self.__components = urllib.parse.ParseResult(**components)
    
    
    def open(self):
        print('OPEN', self)
        request = urllib.request.Request(str(self))
        return urllib.request.build_opener().open(request)
    
    
    @property
    def path(self):
        return unipath.Path(self.__components.path)
    
    
    @path.setter
    def path(self, path):
        if isinstance(path, list):
            path = re.sub(r'^/+', '/', '/'.join(path))
        
        components = self.__components._asdict()
        components['path'] = path
        
        self.__components = urllib.parse.ParseResult(**components)
    
    
    @property
    def query(self):
        return urllib.parse.parse_qs(self.__components.query)
    
    
    @query.setter
    def query(self, query):
        components = self.__components._asdict()
        components['query'] = self.convert_query_to_string(query)
        
        self.__components = urllib.parse.ParseResult(**components)
    
    
    def read(self, parser = None, decode = True):
        response = self.open()
        content = response.read()
        
        if decode:
            headers = email.message_from_string(str(response.headers))
            
            charset = headers.get_content_charset() \
                or chardet.detect(content)['encoding']
            
            content = content.decode(charset)
        
        if parser:
            return self.__PARSERS_BY_TYPE[parser](content)
        else:
            return content
    
    
    def resolve(self):
        connection = self.open()
        url = type(self)(connection.geturl())
        
        connection.close()
        return url
    
    
    @property
    def scheme(self):
        return self.__components.scheme
    
    
    @scheme.setter
    def scheme(self, scheme):
        components = self.__components._asdict()
        components['scheme'] = scheme
        
        self.__components = urllib.parse.ParseResult(**components)
    
    
    def __eq__(self, that):
        return hash(self) == hash(that)
    
    
    def __hash__(self):
        return hash(str(self))
    
    
    def __lt__(self, that):
        return str(self) < str(that)
    
    
    def __str__(self):
        return urllib.parse.urlunparse(self.__components)


page_url = Url(sys.argv[1])
page_html = page_url.read(parser = 'html')

og_video_url = Url(page_html.xpath('//meta[@property = "og:video"]/@content')[0]).resolve()
config_url = Url(og_video_url.query['CONFIG_URL'][0])

video_uri = config_url.query['uri'][0]
config_xml = config_url.read(parser = 'xml', decode = False)

feed_url = Url(config_xml.xpath('/configuration/player/feed/text()')[0] \
    .strip().format(uri = video_uri))

feed_xml = feed_url.read(parser = 'xml', decode = False)

media_urls = map(Url, feed_xml.xpath('//media:content/@url',
    namespaces= {'media': 'http://search.yahoo.com/mrss/'}))

processes = []

for media_url in media_urls:
    media_xml = media_url.read(parser = 'xml', decode = False)
    
    def total_resolution(rendition):
        [height] = rendition.xpath('@height')
        [width] = rendition.xpath('@width')
        return int(height) * int(width)
    
    highest_rendition = sorted(media_xml.xpath('//rendition'),
        key = total_resolution,
        reverse = True)[0]
    
    rtmp_url = Url(highest_rendition.xpath('src/text()')[0].strip())
    file_name = rtmp_url.path.components()[-1]
    
    print('DUMP', rtmp_url)
    
    rtmpdump = subprocess.Popen(['rtmpdump',
        '--quiet',
        '--resume',
        '--flv', str(file_name),
        '--rtmp', str(rtmp_url)])
    
    processes.append(rtmpdump)

for process in processes:
    process.communicate()
