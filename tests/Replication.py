"""
Tests related to replication.
"""

from tailor.test import GenieTest
from time import sleep

class TableReplication(GenieTest):
    """Test creating a table gets replicated"""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(TableReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT) ENGINE=GenieDB;", hosts=self.master, database='test')
        sleep(1)
        self.assertSqlSame("SHOW CREATE TABLE t1;", database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(TableReplication,self).tearDown()

class DatabaseReplication(GenieTest):
    """Test creating a table in a new database gets replicated"""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(DatabaseReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP DATABASE IF EXISTS test_db;", self.master)

    def runTest(self):
        self.assertSqlSuccess("CREATE DATABASE test_db; USE test_db; CREATE TABLE t1 (c1 INT) ENGINE=GenieDB;", hosts=self.master)
        sleep(1)
        self.assertSqlSame("SHOW CREATE TABLE t1;", database='test_db')

    def tearDown(self):
        self.runSql("DROP DATABASE test_db;", self.master)
        super(DatabaseReplication,self).tearDown()

class InsertReplication(GenieTest):
    """Test inserts are replicated"""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(InsertReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT) ENGINE=GenieDB;", hosts=self.master, database='test')
        self.assertSqlSuccess("INSERT INTO t1 VALUES (4), (2);", self.master, database='test')
        sleep(1)
        self.assertSqlSuccess("INSERT INTO t1 VALUES (3), (1);", self.slave, database='test')
        sleep(1)
        self.assertSqlEqual("SELECT * FROM t1 ORDER BY c1 DESC;", "c1\n4\n3\n2\n1\n", database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(InsertReplication,self).tearDown()

class UniqueSecondaryReplication(GenieTest):
    """Test secondary unique keys are respected across different hosts."""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(UniqueSecondaryReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT PRIMARY KEY, c2 INT, UNIQUE INDEX idx(c2)) ENGINE=GenieDB;", hosts=self.master, database='test')
        self.assertSqlSuccess("INSERT INTO t1 VALUES (1,3);", self.master, database='test')
        sleep(1)
        self.assertSqlFailure("INSERT INTO t1 VALUES (2,3);", self.slave, database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(UniqueSecondaryReplication,self).tearDown()

class UpdateReplication(GenieTest):
    """Test updates are replicated"""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(UpdateReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT) ENGINE=GenieDB;", hosts=self.master, database='test')
        self.assertSqlSuccess("INSERT INTO t1 VALUES (4), (2);", self.master, database='test')
        sleep(1)
        self.assertSqlSuccess("INSERT INTO t1 VALUES (3), (1);", self.slave, database='test')
        sleep(1)
        self.assertSqlSuccess("UPDATE t1 SET c1=5 WHERE c1=3;", self.master, database='test')
        self.assertSqlSuccess("UPDATE t1 SET c1=6 WHERE c1=4;", self.slave, database='test')
        sleep(1)
        self.assertSqlEqual("SELECT * FROM t1 ORDER BY c1 DESC;", "c1\n6\n5\n2\n1\n", database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(UpdateReplication,self).tearDown()

class DeleteReplication(GenieTest):
    """Test deletes are replicated"""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(DeleteReplication, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT) ENGINE=GenieDB;", hosts=self.master, database='test')
        self.assertSqlSuccess("INSERT INTO t1 VALUES (4), (2);", self.master, database='test')
        sleep(1)
        self.assertSqlSuccess("INSERT INTO t1 VALUES (3), (1);", self.slave, database='test')
        sleep(1)
        self.assertSqlSuccess("DELETE FROM t1 WHERE c1=3;", self.master, database='test')
        self.assertSqlSuccess("DELETE FROM t1 WHERE c1=4;", self.slave, database='test')
        sleep(1)
        self.assertSqlEqual("SELECT * FROM t1 ORDER BY c1 DESC;", "c1\n2\n1\n", database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(DeleteReplication,self).tearDown()

class ConflictResolution(GenieTest):
    """Test two version of the same record are reconciled."""
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient Hosts")
        super(ConflictResolution, self).setUp()
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
        self.assertSqlSuccess("DROP TABLE IF EXISTS t1;", self.master, database='test')

    def runTest(self):
        self.assertSqlSuccess("CREATE TABLE t1 (c1 INT PRIMARY KEY, c2 INT) ENGINE=GenieDB;", hosts=self.master, database='test')
        sleep(1)
        self.setHostDelay(delay=500)
        self.assertSqlSuccess("INSERT INTO t1 VALUES (1, RAND()*100000);", database='test')
        sleep(1)
        self.clearHostDelay()
        self.assertSqlSame("SELECT * FROM t1 ORDER BY c1 DESC;", database='test')
        self.assertSqlEqual("SELECT count(*) AS count FROM t1;", "count\n1\n", database='test')

    def tearDown(self):
        self.runSql("DROP TABLE t1;", self.master, database='test')
        super(ConflictResolution,self).tearDown()
