# This file is part of gnome-tweak-tool.
#
# Copyright (c) 2011 John Stowers
#
# gnome-tweak-tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gnome-tweak-tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gnome-tweak-tool.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging

from gi.repository import GObject
from gi.repository import Soup, SoupGNOME

class ExtensionsDotGnomeDotOrg(GObject.GObject):

    __gsignals__ = {
      "got-extensions": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,)),
      "got-extension-info": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
            (GObject.TYPE_PYOBJECT,)),
    }

    IDX_PAGE_NUM = 0
    IDX_NUM_PAGES = 1

    def __init__(self, shell_version_tuple):
        GObject.GObject.__init__(self)
        self._session = Soup.SessionAsync.new()
        self._session.add_feature_by_type(SoupGNOME.ProxyResolverGNOME)

        self._shell_version_tuple = shell_version_tuple
        self._extensions = {}

    def _query_extensions_finished(self, msg, url, pages):
        if msg.status_code == 200:
            #server returns a list of extensions which may contain duplicates, dont know
            resp = json.loads(msg.response_body.data)
            for e in resp["extensions"]:
                self._extensions[e["uuid"]] = e

            #first time
            if pages[self.IDX_NUM_PAGES] == -1:
                pages[self.IDX_NUM_PAGES] = int(resp["numpages"])

            #finished
            if pages[self.IDX_PAGE_NUM] == pages[self.IDX_NUM_PAGES]:
                self.emit("got-extensions", self._extensions)
            else:
            #get next page
                url = url.replace(
                        "page=%d" % pages[self.IDX_PAGE_NUM],
                        "page=%d" % (pages[self.IDX_PAGE_NUM] + 1))
                pages[self.IDX_PAGE_NUM] = pages[self.IDX_PAGE_NUM] + 1
                self._queue_query(url, pages)

    def _query_extension_info_finished(self, msg):
        if msg.status_code == 200:
            self.emit("got-extension-info", json.loads(msg.response_body.data))

    def _queue_query(self, url, pages):
        logging.debug("Query URL: %s" % url)
        message = Soup.Message.new('GET', url)
        message.connect("finished", self._query_extensions_finished, url, pages)
        self._session.queue_message(message, None, None)

    def query_extensions(self):
        url = "https://extensions.gnome.org/extension-query/?"

        ver = self._shell_version_tuple
        if ver[1] % 2:
            #if this is a development version (odd) then query the full version
            url += "shell_version=%d.%d.%d&" % ver
        else:
            #else query in point releases up to the current version, and filter duplicates
            #from the reply
            url += "shell_version=%d.%d&" % (ver[0],ver[1])
            for i in range(1,ver[2]+1):
                url += "shell_version=%d.%d.%d&" % (ver[0],ver[1], i)

        pages = [1,-1]
        url += "page=1"

        self._queue_query(url, pages)

    def query_extension_info(self, extension_uuid):
        if extension_uuid in self._extensions:
            print "CACHED"
            self.emit("got-extension-info", self._extensions[extension_uuid])
            return

        url = "https://extensions.gnome.org/extension-info/?uuid=%s" % extension_uuid
        logging.debug("Query URL: %s" % url)
        message = Soup.Message.new('GET', url)
        message.connect("finished", self._query_extension_info_finished)
        self._session.queue_message(message, None, None)

    def get_download_url(self, extinfo):
        url = "https://extensions.gnome.org/download-extension/%s.shell-extension.zip?version_tag=%d"
        #version tag is the pk in the shell_version_map
        #url = url % (extinfo["uuid"], 


if __name__ == "__main__":
    import pprint
    from gi.repository import Gtk, GLib

    def _got_ext(ego, extensions):
        print "="*80
        pprint.pprint(extensions.values())

    def _got_ext_info(ego, extension):
        pprint.pprint(extension)

    logging.basicConfig(format="%(levelname)-8s: %(message)s", level=logging.DEBUG)

    e = ExtensionsDotGnomeDotOrg((3,4,1))

    e.connect("got-extensions", _got_ext)
    e.connect("got-extension-info", _got_ext_info)

    e.query_extensions()
    #e.query_extensions((3,4,0))
    #e.query_extensions((3,3,2))
    e.query_extension_info("user-theme@gnome-shell-extensions.gcampax.github.com")

    Gtk.main()