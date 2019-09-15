#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import queue
from hashlib import md5

import requests
from threading import Thread

username = ''
password = ''
course_id = []  # string[]

# settings
thread_num = 5
timeout = 1
full_course_exit = True

# Disable SSL Errors
requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

session = requests.Session()

url_prefix = 'https://10.60.65.8/ntms/'

session.post(url_prefix + 'j_spring_security_check', data={
    'j_username': username,
    'j_password': '' + md5(('UIMS' + username + password).encode()).hexdigest(),
    'mousePath': 'RGwABRAABaQAwBiQBQBrQCAByQDAB7QEQCCQFQCKQGgCTQHgCaQJQCiQKwCrQMACyQNQC7QOgDDQPwDKQQwDTQRgDaQSQDjRTQDrRTgDySUQD7SUwECSVAELSVwETTWQEaTWgEjTWwEqUXQEzUXgE7VYQFCVYgFSWZAFbWZgFqWZwFzWaAF6WagGDWawGLXbQGSXbgGbXbwGiXcQGrXcwGzXdQG6XeAHDXegHKXfAHTXfwHbXgQHiXgwHrXhQHyXhgH8XiAIDXigIKXjAITXjQIaXjwIjXkQIrXkgIyXlAI7XlgJCXmAJLXmgJTXnAJaXnwJjYoQJqYowJzYpQJ7YpwKCYqgKLYrAKSYrgKbYsAKjYsgKqYtAKzYtQK6YtwLDYuALLYuQLTYugLbYugLiYuwLqZvQLzZvgMCZvgMLZvwMSZwAMbZwQMjZwwMyZxAM6axQNCaxgNLaxwNSbyQNabygNjbywNqczQNyczwOCczwOKc0QOSc0gOac0wOid1QOrd1QO6d1gPCd1wPKe2QPTe2QPie2gPqe2wPyf3AP7f3QQCf3gQLf3wQTg4AQag4QQjg4gQqg4wQyg5AQ7g5QRCg5gRLtzgK/'
}, verify=False)
rest_work = queue.Queue()
result = queue.Queue()


class Worker(Thread):
    thread_no = 0

    def __init__(self, rest_work, result, timeout, **kwargs):
        Thread.__init__(self, **kwargs)
        self.setDaemon(True)
        self.id = Worker.thread_no
        Worker.thread_no += 1
        self.timeout = timeout
        self.start()

    def run(self):
        while True:
            try:
                _callable, args, kwargs = rest_work.get(timeout=self.timeout)
                res = _callable(*args, **kwargs)
                result.put(res)
            except queue.Empty:
                break
            except:
                print('worker[%d]' % self.id + ' occurred an error')


def status(*args, **kwargs):
    if not result.empty():
        return result.get(*args, **kwargs)
    else:
        return None


class Manager:
    def __init__(self, num_of_threads):
        self.workers = []
        self.recruit(num_of_threads)

    def recruit(self, num_of_threads):
        for i in range(num_of_threads):
            worker = Worker(rest_work, result, timeout)
            self.workers.append(worker)

    def supervise(self):
        while len(self.workers):
            try:
                worker = self.workers.pop()
                worker.join()
                if worker.isAlive():
                    self.workers.append(worker)
            except list.empty:
                print(
                    'Do not have enough living workers, please increase the num_of_threads.')
                break
            except:
                print('Something error, retrying...')


class json_exp(Exception):
    def __init__(self):
        # Debug
        pass


def add(callable, *args, **kwargs):
    rest_work.put((callable, args, kwargs))


def send_packet(datastr, url):
    headers = dict()
    headers['Content-Type'] = 'application/json'
    ret = session.post(url, json.dumps(json.loads(datastr)).encode(), headers, verify=False)
    return ret


def check_state(data):
    try:
        j = json.loads(data)
        ret = j['errno']
    except:
        raise json_exp()
    finally:
        return ret


def check_msg(data):
    try:
        j = json.loads(data)
        ret = j['msg']
    except:
        raise json_exp()
    finally:
        return ret


def thread(courseID):
    print('Course ' + courseID + ' is selecting ...')
    while True:
        try:
            ret = send_packet('{"lsltId":"%s","opType":"Y"}' % courseID,
                              url_prefix + 'action/select/select-lesson.do').text
            state = check_state(ret)
            msg = check_msg(ret)
            if state == 1410:
                print('课程 ' + courseID + ' 选课成功！')
                return
            elif state == 2080:
                if full_course_exit:
                    print('课程 ' + courseID + ': ' + msg)
                    return
            else:
                print('课程 %s: 错误 %d: %s' % (courseID, state, msg))
        except:
            raise json_exp()
            continue


if __name__ == "__main__":
    while True:
        try:
            manager = Manager(len(course_id))
            for i in course_id:
                add(thread, i)
            manager.supervise()
            while True:
                res = status()
                if res is None:
                    print('选课完成！')
                    break
        except json_exp:
            print('出现错误，重连中…')
            continue
        break
