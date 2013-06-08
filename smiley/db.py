import contextlib
import logging
import pkgutil
import sqlite3

from smiley import jsonutil

LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def transaction(conn):
    c = conn.cursor()
    try:
        yield c
    except:
        conn.rollback()
        raise
    else:
        conn.commit()


class DB(object):
    """Database connection and API.
    """

    def __init__(self, name):
        self.conn = sqlite3.connect(name)
        # Use Row, instead of just lists/tuples
        self.conn.row_factory = sqlite3.Row
        # Try to select some data and create the schema if we can't.
        try:
            cursor = self.conn.cursor()
            cursor.execute('select * from run')
            LOG.debug('database already initialized')
        except sqlite3.OperationalError:
            LOG.debug('initializing database')
            schema = pkgutil.get_data('smiley', 'schema.sql')
            cursor.executescript(schema)
        return

    def start_run(self, run_id, cwd, description, start_time):
        "Record the beginning of a run."
        with transaction(self.conn) as c:
            c.execute(
                """
                INSERT INTO run (id, cwd, description, start_time)
                VALUES (:id, :cwd, :description, :start_time)
                """,
                {'id': run_id,
                 'cwd': cwd,
                 'description': description,
                 'start_time': start_time}
            )

    def end_run(self, run_id, end_time, message, traceback):
        "Record the end of a run."
        with transaction(self.conn) as c:
            c.execute(
                """
                UPDATE run
                SET
                    end_time = :end_time,
                    error_message = :message,
                    traceback = :traceback
                WHERE id = :id
                """,
                {'id': run_id,
                 'end_time': end_time,
                 'message': message,
                 'traceback': jsonutil.dumps(traceback)},
            )

    def trace(self, run_id, event,
              func_name, line_no, filename,
              trace_arg, locals,
              timestamp):
        "Record an event during a run."
        with transaction(self.conn) as c:
            c.execute(
                """
                INSERT INTO trace
                (run_id, event,
                 func_name, line_no, filename,
                 trace_arg, locals,
                 timestamp)
                VALUES
                (:run_id, :event,
                 :func_name, :line_no, :filename,
                 :trace_arg, :locals,
                 :timestamp)
                """,
                {'run_id': run_id,
                 'event': event,
                 'func_name': func_name,
                 'line_no': line_no,
                 'filename': filename,
                 'trace_arg': jsonutil.dumps(trace_arg),
                 'locals': jsonutil.dumps(locals),
                 'timestamp': timestamp,
                 }
            )
