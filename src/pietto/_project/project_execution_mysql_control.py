"""One bounded supervisor for one exclusively owned MySQL attempt."""

import threading
import time

from pietto._project.project_execution_mysql_context import EPOCH_SQL
from pietto._project.project_execution_mysql_native import failure, transport_state

__all__: tuple[str, ...] = ()


class MySQLControl:
    def __init__(self, owner):
        self.owner = owner
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.thread = threading.Thread(
            target=self._run, name="pietto-mysql-control-" + owner.attempt
        )
        owner.control_events.append(("thread_registered", self.thread.name))

    def start(self):
        self.thread.start()

    def _run(self):
        owner = self.owner
        while not self.stop.is_set():
            remaining = owner._started + owner.request.limits.seconds - time.monotonic()
            if remaining <= 0:
                owner.deadline_expired = True
                owner._cancel.set()
            if owner._cancel.is_set():
                self._interrupt()
                return
            self.wake.wait(min(0.05, max(remaining, 0.001)))
            self.wake.clear()

    def _interrupt(self):
        owner = self.owner
        # Pin transition/release, not the blocked data call. Cancellation closes
        # this attempt to every subsequent submission before inspecting its id.
        with owner._gate:
            if owner._closed or owner._transaction == "COMMIT_ACK":
                return
            connection, control = owner._owned_connection, owner._control_connection
            if connection is None:
                return
            if (
                control is not None
                and control is owner._owned_control_connection
                and owner._epoch is not None
                and transport_state(connection) == owner._transport
                and transport_state(control) == owner._control_transport
            ):
                cursor = None
                try:
                    cursor = control.cursor(read_timeout=2, write_timeout=2)
                    owner._controls.append(cursor)
                    cursor.execute(
                        EPOCH_SQL, (owner.session_id, owner.request.access.user)
                    )
                    rows = tuple(cursor.fetchall())
                    if rows == (owner._epoch,) and owner._active is not None:
                        cursor.execute("KILL QUERY " + str(owner.session_id))
                        owner._cancel_sent = True
                        owner.control_events.append(
                            ("kill_query_send_returned", owner.session_id)
                        )
                except BaseException as error:
                    owner._cleanup_errors.append(failure(error, "cancel"))
                finally:
                    if cursor is not None:
                        try:
                            cursor.close()
                        except BaseException as error:
                            owner._cleanup_errors.append(
                                failure(error, "cancel_cursor_close")
                            )
                        else:
                            owner._controls.remove(cursor)
            # Socket shutdown does not issue another driver command over a busy
            # rowset. It bounds idle/backpressured attempts and uncertain kills.
            try:
                connection.shutdown()
                owner._discarded = True
                owner.control_events.append(("owned_socket_shutdown", owner.session_id))
            except BaseException as error:
                owner._cleanup_errors.append(failure(error, "cancel_shutdown"))

    def join(self):
        self.stop.set()
        self.wake.set()
        if (
            threading.current_thread() is not self.thread
            and self.thread.ident is not None
        ):
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                raise TimeoutError("MYSQL_CONTROL_JOIN")
