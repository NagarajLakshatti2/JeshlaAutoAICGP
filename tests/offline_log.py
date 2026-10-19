"""Flush per-test progress metadata; omit exception and assertion text."""
import json,re,time,unittest
from datetime import datetime,timezone

class ProgressResult(unittest.TextTestResult):
    def __init__(self,*args,progress,**kwargs):
        super().__init__(*args,**kwargs);self.progress=progress;self.started={};self.outcomes={}
    def startTest(self,test):
        super().startTest(test);self.started[test]=time.perf_counter();self.progress('test_started',test=test.id())
    def addSuccess(self,test):self.outcomes[test]='passed';super().addSuccess(test)
    def addError(self,test,err):self.outcomes[test]='error';super().addError(test,err)
    def addFailure(self,test,err):self.outcomes[test]='failed';super().addFailure(test,err)
    def addSkip(self,test,reason):self.outcomes[test]='skipped';super().addSkip(test,reason)
    def addExpectedFailure(self,test,err):self.outcomes[test]='expected_failure';super().addExpectedFailure(test,err)
    def addUnexpectedSuccess(self,test):self.outcomes[test]='unexpected_success';super().addUnexpectedSuccess(test)
    def addSubTest(self,test,subtest,err):
        if err is not None:self.outcomes[test]='failed_subtest'
        super().addSubTest(test,subtest,err)
    def stopTest(self,test):
        self.progress('test_finished',test=test.id(),status=self.outcomes.pop(test,'interrupted'),duration_seconds=round(time.perf_counter()-self.started.pop(test),3));super().stopTest(test)

def writer(handle):
    def emit(event,**fields):
        if 'test' in fields and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',fields['test']):fields['test']='unidentified_test'
        try:
            handle.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'event':event,**fields})+'\n');handle.flush()
        except OSError:pass
    return emit
