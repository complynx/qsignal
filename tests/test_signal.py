# the inclusion of the tests module is not meant to offer best practices for
# testing in general, but rather to support the `find_packages` example in
# setup.py that excludes installing the "tests" package
import qsignal
import threading
import time
import logging

logging.basicConfig(level=logging.DEBUG)
qsignal.enable_thread_debug_messages = True


to_be_true = threading.Event()
to_be_false = threading.Event()

to_be_notified = threading.Condition()

emitted = None


def set_emitted():
    global emitted, to_be_true
    emitted = qsignal.Signal.emitted()
    to_be_true.set()


def to_be_called():
    global to_be_true
    to_be_true.set()


def not_to_be_called():
    global to_be_false
    to_be_false.set()


class ConditionTester(threading.Thread):
    def run(self):
        to_be_notified.acquire()

        to_be_notified.wait()
        to_be_true.set()

        to_be_notified.release()


class MethodTester(object):
    def to_be_called(self):
        global to_be_true
        to_be_true.set()

    def not_to_be_called(self):
        global to_be_false
        to_be_false.set()


class SignallerTester(qsignal.Signaller):
    my_signal = qsignal.Signal()


def test_simple():
    global to_be_true
    to_be_true.clear()
    s = qsignal.Signal()
    s.connect(to_be_called)

    s()

    assert to_be_true.is_set()


def test_async():
    global to_be_true
    to_be_true.clear()
    s = qsignal.Signal()
    s.connect(to_be_called)

    s.async()

    assert to_be_true.wait(2)


def test_event():
    global to_be_true
    to_be_true.clear()
    s = qsignal.Signal()
    s.connect(to_be_true)

    s.async()

    assert to_be_true.wait(2)


def test_condition():
    global to_be_true
    to_be_true.clear()

    t = ConditionTester()
    t.start()

    s = qsignal.Signal()
    s.connect(to_be_notified)

    s.async()

    assert to_be_true.wait(2)


def test_method():
    global to_be_true
    to_be_true.clear()

    t = MethodTester()

    s = qsignal.Signal()
    s.connect(t.to_be_called)

    s.async()

    assert to_be_true.wait(2)


def test_weakref_function():
    global to_be_true, to_be_false
    to_be_true.clear()
    to_be_false.clear()

    t = lambda: to_be_false.set()   # noqa: E731

    s = qsignal.Signal()
    s.connect(t)
    s.connect(to_be_true)

    del t

    s.async()

    assert to_be_true.wait(2)
    time.sleep(1)  # ensure we've not set to_be_false
    assert not to_be_false.is_set()


def test_weakref_class():
    global to_be_true, to_be_false
    to_be_true.clear()
    to_be_false.clear()

    t = MethodTester()

    s = qsignal.Signal()
    s.connect(t.not_to_be_called)
    s.connect(to_be_true)

    del t

    s.async()

    assert to_be_true.wait(2)
    time.sleep(1)  # ensure we've not set to_be_false
    assert not to_be_false.is_set()


def test_emitted():
    global emitted
    emitted = None

    s = qsignal.Signal()
    s.connect(set_emitted)

    s()

    assert emitted == s


def test_emitted_async():
    global emitted
    to_be_true.clear()
    emitted = None

    s = qsignal.Signal()
    s.connect(set_emitted)

    s.async()

    assert to_be_true.wait(2)
    assert emitted == s


def test_signaller():
    s = SignallerTester()

    assert s.my_signal.emitter == s
    assert s.my_signal.name == 'my_signal'
