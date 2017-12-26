QSignal -- A QT Signal/slot for python
======================================

.. image:: https://travis-ci.org/complynx/qsignal.svg?branch=master
    :target: https://travis-ci.org/complynx/qsignal


This project provides easy to use Signal class for implementing Signal/Slot mechanism in Python.
It does not implement it strictly but rather creates the easy and simple alternative.

Classes
=======

Signal
------

``qsignal.Signal`` is the main class.

To create a signal, just make a ``sig = qsignal.Signal`` and set up an emitter of it. Or create it with
``sig = qsignal.Signal(emitter=foo)``.

To emit it, just call your ``sig()``.
Or emit it in asynchronous mode with the method `async`.

Example:

>>> from qsignal import Signal

>>> # Creating signal
>>> sig = Signal()

>>> # Or
>>> myobject.signal = Signal(emitter=myobject)

>>> # Connecting to signals
>>> sig.connect(callback)
>>> myobject.signal.connect(sig)
>>> myobject.signal.connect(otherobject.callback_method)

>>> # Emitting
>>> sig()
>>> myobject.signal('argument(s)', optional=True)

>>> # Emitting in asynchronous mode
>>> sig.async()

To connect slots to it, pass callbacks into `connect`. The connections are maintained through `weakref`, thus
you don't need to search for them and disconnect whenever you're up to destroy some object.

Signaller
---------

The base class for objects to maintain their Signals.

The only purpose of this class is to automate Signal names and emitter references.

>>> from qsignal import Signal, Signaller

>>> # For example, this is a class...
>>> class MyClass(Signaller):
>>>     my_signal = Signal()

>>> # This is a slot...
>>> def my_slot():
>>>     sig = Signal.emitted()
>>>     assert sig.name == my_signal
>>>     assert sig.emitter.__class__ == MyClass

>>> # And the connections...
>>> o = MyClass()
>>> o.my_signal.connect(my_slot)
>>> #...
>>> o.my_signal()
