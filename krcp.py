# -*- coding: utf-8 -*-
import utils
from utils import ID 

class BQuery(object):
    y = "q"
    t = None # string value representing a transaction ID (no more than 16b)
    q = None # string value containing the method name of the query
    a = None # dictionary value containing named arguments to the query
    def __init__(self, t, q, a):
        self.t = t
        self.q = q
        self.a = a
    def __getitem__(self, key):
        return self.a[key]
    def __str__(self):
        return utils.bencode({"y":self.y, "t":self.t, "q":self.q, "a":self.a})
    def __repr__(self):
        return repr({"y":self.y, "t":self.t, "q":self.q, "a":self.a})
class PingQuery(BQuery):
    def __init__(self, t, id):
        super(PingQuery, self).__init__(t, "ping", {"id" : id})
    def response(self, dht, **kwargs):
        return PingResponse(self.t, dht.myid)

class FindNodeQuery(BQuery):
    def __init__(self, t, id, target):
        super(FindNodeQuery, self).__init__(t, "find_node", {"id" : id, "target" : target})
    def response(self, dht, **kwargs):
        return FindNodeResponse(self.t, dht.myid, dht.get_closest_node(self.a["target"]))

class GetPeersQuery(BQuery):
    def __init__(self, t, id, info_hash):
         super(GetPeersQuery, self).__init__(t, "get_peers", {"id" : id, "info_hash" : info_hash})
    def response(self, dht, ip, **kwargs):
        dht.update_hash(self.a["info_hash"], get=True)
        token = dht.get_token(ip)
        nodes = dht.get_closest_node(self.a["info_hash"])
        values = dht.get_peers(self.a["info_hash"])
        if values:
            return GetPeersResponse(self.t, dht.myid, token, values=values)
        else:
            return GetPeersResponse(self.t, dht.myid, token, nodes=nodes)

class AnnouncePeerQuery(BQuery):
    def __init__(self, t, id, info_hash, port, token, implied_port=None):
        # If implied_port is not None and non-zero, the port argument should be ignored and the source port of the UDP packet should be used as the peer's port instead.
        if implied_port is not None:
            super(AnnouncePeerQuery, self).__init__(t, "announce_peer", {"id" : id, "info_hash" : info_hash, "port" : port, "token" : token, "implied_port" : implied_port})
        else:
            super(AnnouncePeerQuery, self).__init__(t, "announce_peer", {"id" : id, "info_hash" : info_hash, "port" : port, "token" : token})
    def response(self, dht, ip, **kwargs):
        if self.a["token"] != dht.get_token(ip):
            raise ProtocolError("Bad token")
        dht.update_hash(self.a["info_hash"], get=False)
        dht.add_peer(info_hash=self.a["info_hash"], ip=ip, port=self.a["port"])
        return AnnouncePeerResponse(self.t, dht.myid)

class BResponse(object):
    y = "r"
    t = None # string value representing a transaction ID
    r = None # dictionary containing named return values
    def __init__(self, t, r):
        self.t = t
        self.r = r
    def __getitem__(self, key):
        return self.r[key]
    def __str__(self):
        return utils.bencode({"y":self.y, "t":self.t, "r":self.r})
    def __repr__(self):
        return repr({"y":self.y, "t":self.t, "r":self.r})
class PingResponse(BResponse):
    def __init__(self, t, id):
        super(PingResponse, self).__init__(t, {"id" : id})
class FindNodeResponse(BResponse):
    def __init__(self, t, id, nodes):
        super(FindNodeResponse, self).__init__(t, {"id" : id, "nodes" : nodes})
    def __str__(self):
        return utils.bencode({"y":self.y, "t":self.t, "r":{"id" : self.r["id"], "nodes" : "".join((n.compact_info() for n in self.r["nodes"]))}})
class GetPeersResponse(BResponse):
    def __init__(self, t, id, token, values=None, nodes=None):
        if nodes is not None:
            super(GetPeersResponse, self).__init__(t, {"id" : id, "token": token, "nodes":nodes})
        elif values is not None:
            super(GetPeersResponse, self).__init__(t, {"id" : id, "token": token, "values":values})
        else:
            raise ValueError("values or nodes needed")
    def __str__(self):
        if "nodes" in self.r:
            return utils.bencode({"y":self.y, "t":self.t, "r":{"id" : self.r["id"], "token" : self.r["token"], "nodes" : "".join((n.compact_info() for n in self.r["nodes"]))}})
        else:
            return super(GetPeersResponse, self).__str__()
class AnnouncePeerResponse(BResponse):
    def __init__(self, t, id):
        super(AnnouncePeerResponse, self).__init__(t, {"id" : id})

class BError(Exception):
    y = "e"
    t = None # string value representing a transaction ID
    e = None # a list. The first element is an integer representing the error code. The second element is a string containing the error message
    def __init__(self, t, e, **kwargs):
        self.t = t
        self.e = e
        super(BError, self).__init__(*e, **kwargs)
    def __str__(self):
        return utils.bencode({"y":self.y, "t":self.t, "e":self.e})
    def __repr__(self):
        return "%s: %s" % self.e

class MethodUnknownError(BError):
    def __init__(self, t, msg="Method Unknow"):
        super(MethodUnknownError, self).__init__(t=t, e=[204, msg])
class ProtocolError(BError):
    def __init__(self, t, msg="Protocol Error"):
        super(ProtocolError, self).__init__(t=t, e=[203, msg])
class GenericError(BError):
    def __init__(self, t, msg=""):
        super(GenericError, self).__init__(t=t, e=[201, msg])

