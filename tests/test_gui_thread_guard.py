"""Unit test for the worker double-start guard predicate (BACKLOG C1).

`any_thread_running` is the GUI-free predicate behind the NetSimulationTab guard
that refuses to launch a second network worker while one is in flight (two threads
must not mutate the same shared net at once). Duck-typed on isRunning().
"""

from districtheatingsim.gui.utilities import any_thread_running


class _StubThread:
    def __init__(self, running):
        self._running = running

    def isRunning(self):
        return self._running


def test_no_threads_is_not_running():
    assert any_thread_running() is False


def test_none_entries_are_skipped():
    assert any_thread_running(None, None) is False


def test_all_idle_is_false():
    assert any_thread_running(_StubThread(False), _StubThread(False)) is False


def test_one_running_is_true():
    assert any_thread_running(_StubThread(False), None, _StubThread(True)) is True
