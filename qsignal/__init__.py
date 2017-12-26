import threading
import logging
from weakref import WeakSet, WeakKeyDictionary
import inspect


enable_thread_debug_messages = False

try:
    _str_class = basestring
    _method_self = 'im_self'
    _method_func = 'im_func'
except NameError:
    _str_class = str
    _method_self = '__self__'
    _method_func = '__func__'


class SignalThread(threading.Thread):
    """
    A thread to dispatch a signal if it is emitted in asynchronous mode.

    Like in `async_decorator.async`, here the thread gets the info about it's parent thread and logs it up.
    """

    def __init__(self, sig, args, kwargs):
        """
        Sets up necessary parameters like thread name, it's parent's name and id, emitter...

        :param Signal sig: signal reference
        :param args: arguments of the signal call
        :param kwargs: KV arguments of the signal call
        """
        super(SignalThread, self).__init__(name=sig.name)
        self.dispatch_async_signal = sig
        self.args = args
        self.kwargs = kwargs

        self.emitter = sig.emitter
        current = threading.currentThread()
        self.parent = (current.getName(), current.ident)

    def run(self):
        """
        Thread entry point.
        Logs the thread ancestry.
        Starts the signal.
        Logs exceptions if necessary.
        """
        if enable_thread_debug_messages:
            __logger = logging.getLogger(self.__class__.__name__)
            __logger.debug(
                'Thread: %s(%d), called from: %s(%d)' % (self.getName(), self.ident, self.parent[0], self.parent[1]))
        try:
            self.dispatch_async_signal._just_call(*self.args, **self.kwargs)
        except Exception as e:
            if enable_thread_debug_messages:
                __logger.error('Thread: %s(%d) encounted an uncaught exception' % (self.getName(), self.ident))
            raise e


def __has_methods(obj, *methods):
    """
    For ducktype testers.
    Tests for methods to exist on objects.
    :param obj:
    :param methods: (variadic)
    :return:
    """
    for method in methods:
        if not hasattr(obj, method) or not callable(getattr(obj, method)):
            return False
    return True


def __is_event_interface(obj):
    """
    Ducktype-tester for `threading.Event` type.
    Returns `True` if object has callable ``set`` and ``is_set``
    :param obj:
    :return: boolean
    """
    return __has_methods(obj, 'set', 'is_set')


def __is_condition_interface(obj):
    """
    Ducktype-tester for `threading.Condition` type.
    Returns `True` if object has callable ``wait``, ``notify``, ``notify_all``, ``acquire`` and ``release``
    :param obj:
    :return: boolean
    """
    return __has_methods(obj, 'wait', 'notify', 'notify_all', 'acquire', 'release')


def _is_notifyable(obj):
    """
    Ducktype-tester for `threading.Condition` or `threading.Event` type.
    :param obj:
    :return: boolean
    """
    return __is_condition_interface(obj) or __is_event_interface(obj)


def _notify_or_set(obj):
    """
    Activator for `threading.Condition` or `threading.Event`.
    :param obj:
    """
    if __is_condition_interface(obj):
        obj.acquire()
        obj.notify_all()
        obj.release()
    else:
        obj.set()


class Signal(object):
    """
    This class provides Signal-Slot pattern from Qt to python.

    To create a signal, just make a ``sig = Signal`` and set up an emitter of it. Or create it with
    ``sig = Signal(emitter=foo)``.

    To emit it, just call your ``sig()``.
    Or emit it in asynchronous mode with the method `async`.

    Example:

    ..code-block:: python

        # Creating
        sig = Signal()
        # Or
        myobject.signal = Signal(emitter=myobject)

        # Connecting to signals
        sig.connect(callback)
        myobject.signal.connect(sig)
        myobject.signal.connect(otherobject.callback_method)

        # Emitting
        sig()
        myobject.signal('argument(s)', optional=True)

        # Emitting in asynchronous mode
        sig.async()

    To connect slots to it, pass callbacks into `connect`. The connections are maintained through `weakref`, thus
    you don't need to search for them and disconnect whenever you're up to destroy some object.
    """
    name = 'BasicSignal'

    def __init__(self, emitter=None, docstring=None):
        """
        Creates a Signal class with no connections.

        :param emitter: Any object or anything, that is bound to a signal
        :param (basestring) docstring: if necessary, you may provide a docstring for this signal instead of the default
                                       one.
        """
        self._functions = WeakSet()
        self._methods = WeakKeyDictionary()
        self._events = WeakSet()
        self._slots_lk = threading.RLock()
        self.emitter = emitter  # TODO: Make this weakref
        if isinstance(docstring, _str_class):
            self.__doc__ = docstring

    def connect(self, slot):
        """
        Connect a callback ``slot`` to this signal if it is not connected already.
        """
        with self._slots_lk:
            if not self.is_connected(slot):
                if inspect.ismethod(slot):
                    method_self = getattr(slot, _method_self)
                    if method_self not in self._methods:
                        self._methods[method_self] = set()

                    self._methods[method_self].add(getattr(slot, _method_func))
                elif _is_notifyable(slot):
                    self._events.add(slot)
                else:
                    self._functions.add(slot)

    def is_connected(self, slot):
        """
        Check if a callback ``slot`` is connected to this signal.
        """
        with self._slots_lk:
            if inspect.ismethod(slot):
                method_self = getattr(slot, _method_self)
                method_func = getattr(slot, _method_func)
                if method_self in self._methods and method_func in self._methods[method_self]:
                    return True
                return False
            elif _is_notifyable(slot):
                return slot in self._events
            return slot in self._functions

    def disconnect(self, slot):
        """
        Disconnect a ``slot`` from a signal if it is connected else do nothing.
        """
        with self._slots_lk:
            if self.is_connected(slot):
                if inspect.ismethod(slot):
                    self._methods[getattr(slot, _method_self)].remove(getattr(slot, _method_func))
                elif _is_notifyable(slot):
                    self._events.remove(slot)
                else:
                    self._functions.remove(slot)

    @staticmethod
    def emitted():
        """
        As the signal may provide emitter and other stuff related, this function gets the signal that was emitted.

        Note! Uses inspect.

        :return Signal: the signal of the current frame, if any.
        """
        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        self = None  # type: Signal
        for i in outer:
            if 'self' in i[0].f_locals and isinstance(i[0].f_locals['self'], Signal):
                self = i[0].f_locals['self']
                break

        del frame
        del outer
        return self

    def __debug_frame_message(self):
        """
        Outputs a name and a line on which a signal was caught. Debug info.
        """
        if not enable_thread_debug_messages:
            return
        logger = logging.getLogger(self.__class__.__name__)
        frame = inspect.currentframe()
        outer = inspect.getouterframes(frame)
        signal_frame = outer[2]
        try:
            logger.handle(logger.makeRecord(logger.name, logging.DEBUG, signal_frame[1], signal_frame[2],
                                            signal_frame[4][0].strip() + " -> " + self.name, (), None, "emit"))
        finally:
            del signal_frame
            del outer
            del frame

    def async(self, *args, **kwargs):
        """
        Emits the signal in the asynchronous mode. Arguments are passed to the callbacks.

        Variadic.
        :return SignalDispatcher:
        """
        self.__debug_frame_message()
        sd = SignalThread(self, args, kwargs)
        sd.start()
        return sd

    def __call__(self, *args, **kwargs):
        """
        Emits the signal in the synchronous mode. Arguments are passed to the callbacks.

        Variadic, Reentrant.
        """
        self.__debug_frame_message()
        self._just_call(*args, **kwargs)
        return self

    def _just_call(self, *args, **kwargs):
        with self._slots_lk:
            # Call handler for events
            for ev in self._events:
                _notify_or_set(ev)

            # Call handler functions
            for func in self._functions:
                func(*args, **kwargs)

            # Call handler methods
            for obj, funcs in self._methods.items():
                for func in funcs:
                    func(obj, *args, **kwargs)


class Signaller(object):
    """
    Object with signals. All signals in it have back references and names.
    """

    def __init__(self):
        """
        Initializes signals
        """
        for i in dir(self):
            v = object.__getattribute__(self, i)
            if isinstance(v, Signal):
                v.name = i
                v.emitter = self
