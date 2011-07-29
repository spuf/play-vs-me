import datetime
from google.appengine.api import memcache

print 'Content-Type: text/plain'
print ''
print ''

while True:
    now = datetime.datetime.now()
    if now.time().second % 10 == 0:
        memcache.set('latest', 'Now is %s' % now.ctime())
