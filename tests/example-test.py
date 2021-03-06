"""Long documentation for test suite!"""

from tailor.test import Test
import time
try:
    from unittest.case import expectedFailure, skip
except:
    from unittest2.case import expectedFailure, skip

class ExTest(Test):
    """Long documentation for test!"""
    
    def runTest(self):
        self.logger.info('3')

class SkippedTest(Test):
    @skip("unconditionally skipped")
    def setUp(self):
        pass

class Fixture(Test):
    
    def setUp(self):
        if len(self.hosts.hosts) < 2:
            self.skipTest("Insufficient hosts to run test")
        self.master = self.hosts.hosts[0]
        self.slave = self.hosts.hosts[1]
    
    def tearDown(self):
        pass

class ExamplePass(Fixture):
    def runTest(self):
        self.assertEqual(self.master.sync_command('hostname'), 0)

class ExampleDiff(Fixture):
    def runTest(self):
        self.assertScriptSame('hostname')
        
class ExampleSlow(Fixture):
    def runTest(self):
        time.sleep(1)

class ExampleException(Fixture):
    def runTest(self):
        raise Exception()

class ExampleFailure(Fixture):
    def runTest(self):
        self.assertTrue(False)

class ExampleExpectedFailure(Test):
    @expectedFailure
    def runTest(self):
        self.assertTrue(False)

class ExampleFailExpectedFailure(Test):
    @expectedFailure
    def runTest(self):
        self.assertTrue(True)
