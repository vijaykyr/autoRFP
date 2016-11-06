#https://cloud.google.com/appengine/docs/python/tools/using-libraries-python-27
# appengine_config.py
from google.appengine.ext import vendor

# Add any libraries install in the "lib" folder.
vendor.add('lib')