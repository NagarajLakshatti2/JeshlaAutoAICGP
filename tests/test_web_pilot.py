"""Web plan binding and native recipe preserve inspected facts and reviewed scope."""
import copy,hashlib,json
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from agent.tools.project_tools import ProjectTools
from integrations.web import gradle
from integrations.web.plans import validate_web_plan
from integrations.web.text_test import text_input_source


class WebPilotTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        self.tools=ProjectTools(str(self.root));self.output=self.root/'outputs/acceptance/run'
        self.patch=patch.object(gradle,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        source=self.root/'requirements.md';source.write_text('Enter Hello World and clear the field.\n',encoding='utf-8')
        self.inspection={'status':'inspected','url':'https://example.test/#inputs','pinned_address':'1.1.1.1',
            'fields':[{'index':1,'tag':'input','type':'text','label':'Account name','placeholder':'Your name','disabled':False,'read_only':False}],
            'buttons':[{'name':'Decline','disabled':False,'in_form':False}]}
        self.file=self.root/'inspection.json';self.file.write_text(json.dumps(self.inspection),encoding='utf-8')
        self.plan={'case_id':'TC-001','field_index':1,'locator_by':'label','locator_text':'Account name','test_value':'Hello World',
            'source_ref':{'file':'requirements.md','start_line':1,'end_line':1,'quote':'Enter Hello World and clear the field.',
                          'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},
            'inspection_file':'inspection.json','inspection_sha256':hashlib.sha256(self.file.read_bytes()).hexdigest(),
            'url':'https://example.test/#inputs','pinned_address':'1.1.1.1','dismiss_button':'Decline',
            'source_traceability':'Y','execution_status':'not_run'}
        for name,text in {'build.gradle':'plugins {}','src/test/java/tests/web/TrialTest.java':'package tests.web; class TrialTest {}'}.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')

    def test_plan_binds_actual_unique_field_and_source(self):
        self.assertEqual(validate_web_plan(self.tools,self.plan)['inspection_binding'],'Y')
        self.assertEqual(validate_web_plan(self.tools,self.plan)['source_traceability'],'Y')

    def test_stale_or_wrong_inspection_cannot_be_used(self):
        for changes in ({'inspection_sha256':'0'*64},{'locator_text':'Guessed label'},{'url':'https://other.test'},
                        {'pinned_address':'8.8.8.8'},{'field_index':True},{'field_index':2},
                        {'dismiss_button':'Submit'},{'test_value':'Invented text'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_web_plan(self.tools,{**self.plan,**changes})

    def test_source_revision_change_blocks_execution(self):
        (self.root/'requirements.md').write_text('Changed requirement.',encoding='utf-8')
        with self.assertRaises(ValueError):validate_web_plan(self.tools,self.plan)

    def test_protected_or_ambiguous_field_is_not_silently_selected(self):
        for changes in ({'read_only':True},{'disabled':True},{'type':'password'}):
            inspection=copy.deepcopy(self.inspection);inspection['fields'][0].update(changes)
            self.file.write_text(json.dumps(inspection),encoding='utf-8')
            plan={**self.plan,'inspection_sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()}
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_web_plan(self.tools,plan)

    def test_template_has_exact_assertions_and_no_site_values(self):
        text=text_input_source('tests.web.TrialTest')
        self.assertIn('package tests.web;',text)
        self.assertIn('Assert.assertEquals(field.inputValue(),value',text)
        self.assertIn('field.click();field.fill("")',text)
        self.assertIn('ControlOrMeta+A',text)
        self.assertIn('failure.png',text);self.assertIn('trace.zip',text)
        self.assertNotIn('qapracticehub',text);self.assertNotIn('Hello World',text)
        self.assertIn('CUSTOM_2_textEntryAndClear',text_input_source('tests.web.TrialTest','CUSTOM-2'))
        for name in ('tests.web.X; delete','outside.TrialTest','../TrialTest'):
            with self.assertRaises(ValueError):text_input_source(name)

    def test_recipe_preparation_does_not_execute_and_preserves_target(self):
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch.object(self.tools,'run_command',side_effect=AssertionError('No execution')) as run:
            result=gradle.prepare_web_pilot(self.tools,self.output,test_class='tests.web.TrialTest',plan=self.plan)
            run.assert_not_called()
        for p,raw in before.items():self.assertEqual((self.root/p).read_bytes(),raw)
        self.assertIn('-Dweb.pilot.target=Account name',result['command'])
        self.assertIn('-Dweb.pilot.value=Hello World',result['command'])
        self.assertEqual(result['timeout'],150)
        script=(self.output/'web-pilot.init.gradle').read_text(encoding='utf-8')
        self.assertIn('testClassesDirs=p.files(classesFolder)',script)
        self.assertNotIn('ReportPortalTestNGListener',script)
        self.assertIn("environment 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD','1'",script)

    def test_invalid_output_or_private_network_pin_never_prepare_a_run(self):
        with self.assertRaises(ValueError):gradle.prepare_web_pilot(self.tools,self.root/'outside',test_class='tests.web.TrialTest',plan=self.plan)
        with self.assertRaises(ValueError):gradle.prepare_web_pilot(self.tools,self.output,test_class='tests.web.TrialTest',plan={**self.plan,'pinned_address':'127.0.0.1'})
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
