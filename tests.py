from unittest import TestCase
import unittest
from mock import MagicMock
from mock import patch
import mock
import mypackage.a
import mypackage.b
import mypackage.c
import types

DEFAULT_VALUE = 1
PATCHED_VALUE = 42
QUERY_DATABASE_DEFAULT_VALUE = 1000000


class MockObjectExamples(TestCase):

    def test_mock(self):
        """ demo the 'viral' spreading nature of mock"""

        m = MagicMock()
        self.assertIsInstance(m, MagicMock)

        # a mock is always callable, and returns its return_value (by default, another mock
        self.assertIsInstance(m(), MagicMock)

        # any arbitrary attribute access will return another mock
        self.assertIsInstance(m.xyz, MagicMock)
        self.assertIsInstance(m['test'], MagicMock)
        self.assertIsInstance(m.foo(), MagicMock)
        self.assertIsInstance(m.just.keep.on()['trucking'], MagicMock)

        # different properties will all have different mock objects returned
        self.assertNotEqual(m.abcd, m.efgh)

        # once referenced, the same mock is always returned
        self.assertEqual(m.abcd, m.abcd)

    def test_mock_truthiness(self):
        m = MagicMock()

        # a mock is always truthy
        self.assertTrue(m.is_authenticated())

        # unless I patch specifically (use __bool__ instead of __nonzero__ in Python 3+)
        m.is_authenticated().__nonzero__ = lambda self: False

        self.assertFalse(m.is_authenticated())

        if m.is_authenticated():
            self.fail()

    def test_mock_magic_methods(self):
        def my_str(self):
            return 'owned'

        m = MagicMock()
        m.__str__ = my_str
        self.assertEqual('owned', str(m))

    def test_mock_attribute_constructor(self):
        m = MagicMock(**{'first_name': 'owned', 'calculate_minimum.return_value': 456})
        self.assertEqual('owned', m.first_name)
        self.assertEqual(456, m.calculate_minimum())

    def test_return_value(self):
        m = MagicMock(return_value=123)
        self.assertEqual(123, m())
        m.return_value = 345
        self.assertEqual(345, m())

    def test_side_effect_with_iterable_values(self):
        m = MagicMock()
        m.side_effect = range(1000)
        self.assertEqual(0, m())
        self.assertEqual(1, m())
        self.assertEqual(2, m())
        self.assertEqual(3, m())
        self.assertEqual(4, m())
        # ... up to 1000. raises StopIteration after that

        m.side_effect = range(3)
        self.assertEqual(0, m())
        self.assertEqual(1, m())
        self.assertEqual(2, m())
        self.assertRaises(StopIteration, m)

    def test_side_effect_with_exception(self):
        m = MagicMock(side_effect=KeyError('foo'))
        self.assertRaises(KeyError, m)

    def test_mock_spec(self):
        pass

    def test_mock_called(self):
        m = MagicMock()
        self.assertFalse(m.called)
        m()
        self.assertTrue(m.called)

    def test_mock_called_with(self):
        m = MagicMock()
        m(1)
        m.assert_called_with(1)

        m(2)
        m.assert_called_with(2)

        # called_with means "the last call", not "ever". calling m.assert_called_with(1) now will raise error
        self.assertRaises(AssertionError, m.assert_called_with, 1)


class PatchExamples(TestCase):
    """Patching fundamentally replaces an ATTRIBUTE on a TARGET OBJECT
    """

    def test_patch_object_as_func_decorator(self):
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        @patch.object(my_instance, '_val', new=PATCHED_VALUE)
        def _test():
            self.assertEqual(PATCHED_VALUE, my_instance.foo())

        _test()

    def test_patch_object_as_context_processor(self):
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        with patch.object(my_instance, '_val', new=PATCHED_VALUE):
            self.assertEqual(PATCHED_VALUE, my_instance.foo())

    def test_patch_object_as_class_decorator(self):
        @patch('mypackage.a.query_database', new=MagicMock(return_value=PATCHED_VALUE))
        class MyNewTestClass(unittest.TestCase):

            def foo(self):
                return mypackage.a.query_database()

            def test_one(self):
                self.assertEqual(PATCHED_VALUE, self.foo())

            def test_two(self):
                self.assertEqual(PATCHED_VALUE, self.foo())

            def other_method(self):
                self.assertNotEqual(PATCHED_VALUE, self.foo())
                self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE, self.foo())

            def runTest(self):
                # just need this due to declaration inside function
                pass

        test_class = MyNewTestClass()

        # test_xxx methods have been patched
        test_class.test_one()
        test_class.test_two()

        # this one was not
        test_class.other_method()

    def test_patch_dict(self):
        d = {'a': 111, 'b': 222}
        with patch.dict(d, values={'a': 333}):
            self.assertEqual(d['a'], 333)
            self.assertEqual(d['b'], 222)

    def test_patching(self):

        self.assertEqual(dir(mypackage.a), ['A_MODULE_VAR', 'QUERY_DATABASE_DEFAULT_VALUE',
                                            '__builtins__', '__doc__', '__file__', '__name__', '__package__',
                                            'double_database', 'fn_referencing_module_var', 'function_with_inner_function',
                                            'function_with_local_alias', 'query_database'])

        self.assertEqual(dir(mypackage.b), ['__builtins__', '__doc__', '__file__', '__name__', '__package__',
                                            'mypackage', 'query_database', 'triple_database', 'triple_database_different_import', 'triple_database_local_import'])

        self.assertEqual(types.ModuleType, type(mypackage.a))
        self.assertEqual(types.FunctionType, type(mypackage.a.query_database))

        self.assertEqual(types.ModuleType, type(mypackage.b))
        self.assertEqual(types.FunctionType, type(mypackage.b.query_database))
        self.assertEqual(types.FunctionType, type(mypackage.b.__dict__['query_database']))
        self.assertEqual(mypackage.b.query_database, mypackage.b.__dict__['query_database'])

        self.assertEqual(mypackage.a.query_database, mypackage.b.query_database)

        with patch('mypackage.b.query_database', new=MagicMock(return_value=PATCHED_VALUE)):
            self.assertNotEqual(mypackage.b.query_database, mypackage.b.mypackage.a.query_database)
            self.assertNotEqual(types.FunctionType, type(mypackage.b.query_database))
            self.assertEqual(types.FunctionType, type(mypackage.b.mypackage.a.query_database))

            self.assertEqual(PATCHED_VALUE, mypackage.b.query_database())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE, mypackage.a.query_database())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE, mypackage.b.mypackage.a.query_database())

        with patch('mypackage.a.query_database', new=MagicMock(return_value=PATCHED_VALUE)):

            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database())
            self.assertEqual(PATCHED_VALUE*3, mypackage.b.triple_database_different_import())

    def test_patch_object_on_instances(self):
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        another_instance = mypackage.c.MyClass(DEFAULT_VALUE)

        with(patch.object(my_instance, 'foo', new=MagicMock(return_value=666))):
            self.assertEqual(666, my_instance.foo())
            self.assertEqual(DEFAULT_VALUE, another_instance.foo())

        with(patch.object(my_instance, '_val', new=777)):
            self.assertEqual(777, my_instance.foo())
            self.assertEqual(DEFAULT_VALUE, another_instance.foo())

    def test_patch_object_on_classes(self):
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        another_instance = mypackage.c.MyClass(DEFAULT_VALUE)

        with(patch.object(mypackage.c.MyClass, 'foo', new=MagicMock(return_value=666))):
            self.assertEqual(666, my_instance.foo())
            self.assertEqual(666, another_instance.foo())

        @patch.object(mypackage.c.MyClass, '_val', new=777)
        def test_patching_instance_var_on_class():
            pass

        # mypackage.c.MyClass does not have the attribute '_val'
        self.assertRaises(AttributeError, test_patching_instance_var_on_class)

    @patch('mypackage.a.query_database', new=MagicMock(return_value=1))
    def test_patch_as_function_decorator(self):
        x = mypackage.a.double_database()
        self.assertEqual(x, 2)

    def test_patch_where(self):
        with patch('mypackage.a.query_database', new=MagicMock(return_value=1)):
            x = mypackage.b.triple_database()

            #!! was not mocked
            self.assertEqual(x, 3000000)

        with patch('mypackage.b.query_database', new=MagicMock(return_value=1)):
            x = mypackage.b.triple_database()

            # was successfully mocked
            self.assertEqual(x, 3)

            x = mypackage.b.triple_database_different_import()

            #! but the other reference was not
            self.assertEqual(x, 3000000)

            with patch('mypackage.b.mypackage.a.query_database', new=MagicMock(return_value=1)):
                y = mypackage.b.triple_database_different_import()

                # now it is
                self.assertEqual(y, 3)

    def test_patch_no_local_namespace_references(self):
        # a common newbie mistake is to think it's possible to somehow patch
        # variables in a function's local namespace. nothing like this will work
        @patch('mypackage.a.function_with_inner_function.inner_func')
        def test():
            return mypackage.a.function_with_inner_function()

        self.assertRaises(AttributeError, test)

        @patch('mypackage.a.function_with_local_alias.my_fn_alias')
        def test():
            return mypackage.a.function_with_local_alias()

        self.assertRaises(AttributeError, test)

    def test_patch_inline_import(self):
        with patch('mypackage.b.query_database', new=MagicMock(return_value=1)):
            x = mypackage.b.triple_database_local_import()

            # impossible to mock
            self.assertEqual(x, 3000000)

    @patch('mypackage.a.A_MODULE_VAR', new=777)
    def test_patch_module_variable(self):
        self.assertEqual(777, mypackage.a.A_MODULE_VAR)

    @patch('mypackage.a.A_MODULE_VAR', new=777)
    def test_patch_module_variable_referenced_by_fn(self):
        self.assertEqual(777, mypackage.a.fn_referencing_module_var())


class PropertyExample(TestCase):

    def test_attempt_to_patch_readonly_property(self):
        my_instance = mypackage.c.MyClass(1)
        self.assertEqual(my_instance.read_only_prop, 1)

        @patch.object(my_instance, 'read_only_prop', new=666)
        def test_patching_readonly_property():
            pass

        self.assertRaises(AttributeError, test_patching_readonly_property)

        def test_setting_readonly_property():
            my_instance.read_only_prop = 666

        # fails for the same reason
        self.assertRaises(AttributeError, test_setting_readonly_property)

    def test_patching_writable_property(self):
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        self.assertEqual(my_instance.writeable_prop, DEFAULT_VALUE)

        @patch.object(my_instance, 'writeable_prop', new=666)
        def test_patching_writable_property():
            self.assertEqual(666, my_instance.writeable_prop)

        # patching the writable property works
        test_patching_writable_property()

    def test_patching_readonly_property_at_class_level(self):
        my_instance = mypackage.c.MyClass(1)

        @patch.object(mypackage.c.MyClass, 'read_only_prop', new=666)
        def _test_patching_readonly_property_with_value():
            self.assertEqual(my_instance.read_only_prop, 666)

        # patching at class level works. we have replaced the property object "read_only_prop" with a simple int
        _test_patching_readonly_property_with_value()

        # why does it work?
        self.assertEqual(int, type(my_instance.read_only_prop))
        self.assertEqual(property, type(mypackage.c.MyClass.read_only_prop))


        # if you need to assert called or change return value multiple times,
        # this form also works
        @patch.object(mypackage.c.MyClass, 'read_only_prop', new_callable=mock.PropertyMock)
        def _test_patching_readonly_property_with_callable(mock_read_only_prop):
            mock_read_only_prop.return_value = 666
            self.assertEqual(my_instance.read_only_prop, 666)
            mock_read_only_prop.assert_called()

            mock_read_only_prop.return_value = 777
            self.assertEqual(my_instance.read_only_prop, 777)

        _test_patching_readonly_property_with_callable()


if __name__ == '__main__':
    unittest.main()
