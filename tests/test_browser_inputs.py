"""Browser text-entry checks: locator ambiguity, protected fields and actual values."""
import copy
import unittest
from unittest.mock import Mock
from agent.tools.browser_inputs import check_text_entry, inspect_input_fields


class BrowserInputTests(unittest.TestCase):
    def fixture(self, *, entered='Hello World', cleared='', **changes):
        page, field = Mock(), Mock()
        page.get_by_placeholder.return_value=field
        page.get_by_label.return_value=field
        page.get_by_role.return_value=field
        field.count.return_value=1;field.is_editable.return_value=True
        base={'tag':'INPUT','type':'text','value':'','placeholder':'Name',
              'placeholder_shown':True,'disabled':False,'readOnly':False,'visible':True}
        base.update(changes)
        field.evaluate.side_effect=[copy.deepcopy(base),copy.deepcopy(base),
            {**base,'value':entered,'placeholder_shown':not bool(entered)},
            {**base,'value':cleared,'placeholder_shown':not bool(cleared)}]
        return page,field

    def test_actual_value_and_backspace_are_checked(self):
        page,field=self.fixture();captures=[]
        result=check_text_entry(page,by='placeholder',target='Name',value='Hello World',capture=captures.append)
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['observations'][1]['value'],'Hello World')
        self.assertEqual(result['observations'][2]['value'],'')
        self.assertTrue(result['placeholder_checks']['shown_after_clearing'])
        self.assertEqual(captures,['initial','entered','cleared'])
        self.assertEqual([c.args[0] for c in field.press.call_args_list],['ControlOrMeta+A','Backspace'])
        field.click.assert_called_once_with()
        self.assertFalse(result['form_submitted'])

    def test_nonempty_wrong_text_does_not_pass(self):
        page,field=self.fixture(entered='Different value')
        result=check_text_entry(page,by='placeholder',target='Name',value='Hello World')
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['checks']['exact_value_retained'])

    def test_clear_failure_does_not_pass(self):
        page,field=self.fixture(cleared='World')
        result=check_text_entry(page,by='placeholder',target='Name',value='Hello World')
        self.assertEqual(result['status'],'failed')
        self.assertFalse(result['checks']['select_all_backspace_cleared'])

    def test_ambiguous_and_missing_fields_stop_before_typing(self):
        for count in (0,2):
            page,field=self.fixture();field.count.return_value=count
            with self.subTest(count=count),self.assertRaisesRegex(ValueError,'exactly one'):
                check_text_entry(page,by='label',target='Name',value='Hello World')
            field.fill.assert_not_called()

    def test_protected_or_unsupported_controls_are_not_changed(self):
        for change in ({'type':'password'},{'type':'email'},{'type':'checkbox'},{'tag':'TEXTAREA'},
                       {'disabled':True},{'readOnly':True},{'visible':False}):
            page,field=self.fixture(**change)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'ordinary text input'):
                check_text_entry(page,by='placeholder',target='Name',value='Hello World')
            field.fill.assert_not_called();field.press.assert_not_called()

    def test_accessible_label_and_role_are_supported_without_site_ids(self):
        for by in ('label','role'):
            page,field=self.fixture()
            self.assertEqual(check_text_entry(page,by=by,target='Account name',value='Hello World')['status'],'passed')
            if by=='label':page.get_by_label.assert_called_once_with('Account name',exact=True)
            else:page.get_by_role.assert_called_once_with('textbox',name='Account name',exact=True)

    def test_invalid_input_bounds_stop_before_page_access(self):
        for changes in ({'by':'css'},{'target':''},{'value':''},{'value':'x'*501}):
            page=Mock();args={'by':'label','target':'Name','value':'Hello World'};args.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):check_text_entry(page,**args)
            self.assertFalse(page.mock_calls)

    def test_overlay_prevents_typing_rather_than_being_bypassed(self):
        page,field=self.fixture()
        field.click.side_effect=RuntimeError('Pointer blocked by overlay')
        with self.assertRaisesRegex(RuntimeError,'Pointer blocked'):
            check_text_entry(page,by='label',target='Name',value='Hello World')
        field.fill.assert_not_called();field.press.assert_not_called()

    def test_inspection_is_bounded(self):
        page=Mock()
        for limit in (True,0,101):
            with self.subTest(limit=limit),self.assertRaises(ValueError):inspect_input_fields(page,limit)
        page.locator.assert_not_called()
        inspect_input_fields(page,10)
        page.locator.assert_called_once_with('input')


if __name__=='__main__':unittest.main()
