from google.appengine.api import memcache

print 'Content-Type: text/plain'
print ''
print memcache.get_stats()

memcache.flush_all()