import sqlite3
import tempfile
from pathlib import Path
import unittest
from task_memory import TaskMemory


class MemoryTests(unittest.TestCase):
    def test_persistence_and_duplicate_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.db'
            m=TaskMemory(path,create=True)
            m.append('task_1',17,25,42)
            with self.assertRaises(sqlite3.IntegrityError):
                m.append('task_1',1,2,3)
            m.close()
            m=TaskMemory(path)
            self.assertEqual(m.get('task_1')['result'],42)
            self.assertIsNone(m.get("' OR 1=1 --"))
            m.close()
            with self.assertRaises(FileExistsError):
                TaskMemory(path,create=True)

    def test_invalid_receipts_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=TaskMemory(Path(tmp)/'memory.db',create=True)
            for args in [('x',True,1,2),('x',1,2,99),('../x',1,2,3)]:
                with self.assertRaises(ValueError):m.append(*args)
            self.assertIsNone(m.get('x'))
            m.close()

    def test_missing_database_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'absent.db'
            with self.assertRaises(ValueError):TaskMemory(path)
            self.assertFalse(path.exists())


if __name__=='__main__':unittest.main()
