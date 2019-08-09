import concurrent
import datetime
import logging
import os
import queue
import re
import socket
import argparse
import threading
from multiprocessing.dummy import Pool as ThreadPool
import concurrent
import concurrent.futures

class OtusServer:
    SOCKET_SERVER_HOST = 'localhost'
    SOCKET_SERVER_PORT = 9999
    SOCKET_SERVER = (SOCKET_SERVER_HOST, SOCKET_SERVER_PORT)
    PACKAGE_SIZE = 1024
    MAX_LISTENER_NUMBER = 5
    DOCUMENT_ROOT = 'DOCUMENT_ROOT'
    empty_values = (None,(),[],{})
    WORKERS_AMOUNT = 1

    #200 403 404 405
    OK_HEADER = b'HTTP/1.x 200 OK\r\n'
    NOT_FOUND_HEADER = b'HTTP/1.x 404 Bad Request\r\n'
    FORBIDDEN_REQUEST_HEADER = b'HTTP/1.x 403 Forbidden\r\n'
    NOT_ALLOWED_REQUEST_HEADER = b'HTTP/1.x 405 Method Not Allowed\r\n'
    CONTENT_TYPE_HEADER = b'Content-Type: text/html; charset=UTF-8\r\n'
    # BASIC_PAGE = 'http://' + str(SOCKET_SERVER_HOST) + ':' + str(SOCKET_SERVER_PORT) + '/'
    SERVER_HEADER = b'Server: Otus Server/1.1(Win64)\r\n'

    logging.basicConfig(filename=None, level=logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler

    def arg_parser(self):
        argument_parser = argparse.ArgumentParser()
        argument_parser.add_argument('-w', type=int, help='workers amount')
        argument_parser.add_argument('-r', type=str, help='DOCUMENT_ROOT directory')
        result_args = argument_parser.parse_args()
        if result_args.r not in OtusServer.empty_values:
            OtusServer.DOCUMENT_ROOT = result_args.r
        if result_args.w not in OtusServer.empty_values:
            OtusServer.WORKERS_AMOUNT = result_args.w

    def get_content_type(self, path):
        if path.endswith('/') or path.endswith('.html') or path.count('.') == 0:
            return b'Content-Type: text/html; charset=UTF-8\r\n'
        elif path.endswith('.css'):
            return b'Content-Type: text/css\r\n'
        elif path.endswith('.js'):
            return b'Content-Type: application/javascript\r\n'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return b'Content-Type: image/jpeg\r\n'
        elif path.endswith('.png'):
            return b'Content-Type: image/png\r\n'
        elif path.endswith('.gif'):
            return b'Content-Type: image/gif\r\n'
        # elif path.endswith('.swf'): ???
        #     return b'Content-Type: application/javascript\r\n' ???
        elif path.endswith('.ico'): #???
            return b'Content-Type: image/vnd.microsoft.icon\r\n' #???

    def send_html_header(self, user_socket,path, code=200, content_length=1):
        if code == 200:
            user_socket.send(OtusServer.OK_HEADER)
            user_socket.send(b'Date: ' + str(datetime.datetime.now()).encode('utf-8') + b'\r\n') #date_header
            user_socket.send(OtusServer.SERVER_HEADER)
            user_socket.send(b'ContentLength: ' + str(os.path.getsize(path)).encode() + b'\r\n')
            user_socket.send(b'Connection: close\r\n') ## close? ## Is that right?? What need to write ??
        if code == 403: user_socket.send(OtusServer.FORBIDDEN_REQUEST_HEADER)
        if code == 404: user_socket.send(OtusServer.NOT_FOUND_HEADER)
        if code == 405: user_socket.send(OtusServer.NOT_ALLOWED_REQUEST_HEADER)
        # user_socket.send(CONTENT_TYPE_HEADER)
        user_socket.send(self.get_content_type(path))
        user_socket.send(b'\r\n')

    def casting_html_to_byte(self, html_str):
        return html_str.replace(b'\n',b'').replace(b'\r',b'').replace(b'\t',b'')

    def is_path_exist(self, path_to_page):
        return os.path.exists(OtusServer.DOCUMENT_ROOT + path_to_page)

    def _get_result_path_page_helper(self,path_to_page):
        path_array = path_to_page.replace('/', ' ').split()
        result_path = os.path.join(OtusServer.DOCUMENT_ROOT, *path_array)
        if result_path.strip() == OtusServer.DOCUMENT_ROOT or os.path.isdir(result_path.replace('/', '\\')):
            result_path = os.path.join(result_path, 'index.html')
        return result_path

    def _get_result_path_file_helper(self,path_to_file): ####???
        path_array = path_to_file.replace('/', ' ').split()
        result_path = os.path.join(OtusServer.DOCUMENT_ROOT, *path_array)
        return result_path

    def get_page(self, user_socket, path_to_page):
        if self.is_path_exist(path_to_page):
            result_path = self._get_result_path_page_helper(path_to_page)
            self.send_html_header(user_socket,result_path,200)
            with open(result_path, 'rb') as html_page:
                file_str = html_page.read()
                user_socket.sendall(self.casting_html_to_byte(file_str))
        else:
            self.send_html_header(user_socket,path_to_page, 404)

    def get_file(self, path, user_socket):
        with open(path, 'rb') as file:
            user_socket.sendall(file.read())

    def method_handler(self, request, user_socket):
        str_data = request.decode('utf-8')
        method, path, type = str_data.split('\n')[0].split()
        if method == "GET" or method == "HEAD":
            if re.search(r'(\.css|\.js|\.jpg|\.jpeg|\.png|\.gif|\.swf)', path) and method == "GET":
                temp = str_data.split('\n')
                #searching referer_url -- need get package name
                for temp_line in temp:
                    if temp_line.count('Referer:') == 1:
                        referer = temp_line.split()[1].replace('\r','').replace('\n','').replace('\t','')
                full_url_path = (referer + path).replace((r'http://' + OtusServer.SOCKET_SERVER_HOST + ':' + str(OtusServer.SOCKET_SERVER_PORT)),'')
                path = OtusServer.DOCUMENT_ROOT + full_url_path.replace('/','\\')
                if path.count('%20') > 0: path = path.replace('%20', '')
                self.send_html_header(user_socket, path, 200)
                self.get_file(path=path, user_socket=user_socket)
            else:
                self.get_page(user_socket, path)
        else: #else 405 error
            self.send_html_header(user_socket,path, 405)
            user_socket.sendall(b"that's ERROR-request")

    def _get_client_response(self,connection):
        data = b''
        while True:
            chunk = connection.recv(1024)
            data += chunk
            if not chunk or chunk.endswith(b'\r\n\r\n'):
                break
        return data

    def run_server(self):
        serv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serv_socket.bind(OtusServer.SOCKET_SERVER)
        serv_socket.listen(OtusServer.MAX_LISTENER_NUMBER)
        self.arg_parser()
        logging.info(f'Server start work: {OtusServer.SOCKET_SERVER_HOST}:{OtusServer.SOCKET_SERVER_PORT}')

        #TODO
        # Если соединение не закрывается - то страница как бы и не загрузилась.
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                while True:
                    try:
                        connection, address = serv_socket.accept()

                        # connection.settimeout(5)
                        ## Это ужас надо чтобы соединение закрывалось
                        # почему оно не закрывается??

                        logging.info(f"new connection from {address}")
                        data = self._get_client_response(connection)

                        if data:
                            executor.submit(self.method_handler, data, connection)
                        logging.info(f'close {address}')
                    except Exception as ex:
                        logging.error(ex)
                    finally:
                        connection.close()
        except Exception as ex:
            logging.error(ex)
        finally:
            serv_socket.close()

otus_server = OtusServer()
otus_server.run_server()