import sys
import os

import zmq
from tabulate import tabulate

class MsgToXnode(object):
    REQ_ID = 0

    def __init__(self, xquery):
        self.xquery = xquery

    def to_json(self, ts=0):
        self.REQ_ID += 1
        return {"req_id": str(self.REQ_ID),
                "widget_id": "xray-cli",
                "query": self.xquery,
                "timestamp": int(ts)}


class NoNodesError(Exception):
    pass


class XrayCli(object):
    XRAY_NODES_PATH = '/tmp/xray/'

    def __init__(self):
        self.ctx = None
        self.request = None
        self.nodes_list = self.get_nodes()

    def get_nodes(self):
        try:
            nodes = os.listdir(self.XRAY_NODES_PATH)
            nodes = [[node] for node in nodes]
            nodes.insert(0, ["nodes"])
            return nodes
        except OSError:
            return [["NODE"], []]

    def init_socket(self, node):
        self.ctx = zmq.Context()
        self.request = self.ctx.socket(zmq.REQ)
        # self.request.setsockopt(zmq.IDENTITY, "xraycli-" + str(os.getpid()))
        self.request.setsockopt(zmq.RCVTIMEO, 1000)
        self.request.setsockopt(zmq.SNDTIMEO, 1000)
        self.request.connect('ipc://{}/{}'.format(self.XRAY_NODES_PATH, node))

    def send_recv(self, node, msg):
        self.init_socket(node)

        # print(">SEND ", node, ": ", msg.to_json())
        # self.request.send(node.encode('ascii'), zmq.SNDMORE)
        self.request.send_json(msg.to_json())

        node_id = self.request.recv_string(encoding='ascii')
        msg = self.request.recv_json()
        # print("<RECV", msg)
        return msg["result_set"]

    def get_result_set(self, full_xpath):
        if full_xpath == '/':
            return self.nodes_list
        if full_xpath[-1] != "/":
            full_xpath += "/"
        node, node_xpath = full_xpath.split('/', 2)[1:]
        if node_xpath == '':
            node_xpath = "/"
        return self.send_recv(node, MsgToXnode(node_xpath))

    def run(self, full_xpath):
        result_set = self.get_result_set(full_xpath)
        table = tabulate(result_set[1:], headers=result_set[0])
        print(table)

    def close(self):
        try:
            self.request.close()
            self.ctx.destroy()
        except Exception:
            pass


def usage():
    print("usage:")
    print("\txraycli <path>")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        usage()
        exit(-1)
    xcli = XrayCli()
    try:
        xcli.run(sys.argv[1])
    finally:
        xcli.close()


