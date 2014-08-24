"""
This test suite is intended to demonstrate sample usage of the python mock library.
Much of this is already covered in the mock documentation, but this hopefully
adds a few useful examples, calls out some subtleties, and addresses
some common misunderstandings.

It is intended to be read in-order, as a primer.
Almost like a technical blog post written as a test suite.

Run these tests with `python tests.py`
"""

import unittest
from unittest import TestCase
import mock
from mock import Mock, MagicMock, patch

import mypackage.a
import mypackage.b
import mypackage.c
import types

################################################################################################
# PART 1: The Mock class
# The mock library has two major components that are separate, but work powerfully in tandem.
# The first is the Mock class (and subclasses). The second are the 'patch' helpers.
# First, we will demonstrate usage of the Mock class.
################################################################################################


class MockObjectBasics(TestCase):
    """Demonstates the basics of the 'Mock' class."""

    def test_mock(self):
        """A Mock object is callable, and you can configure
        this callable's return value. By default it returns
        another Mock instance, created on first access.
        Any arbitrary attribute access also creates & returns another
        mock instance. This 'spreads' to form a tree of Mock objects"""

        m = Mock()
        self.assertIsInstance(m, Mock)

        # a mock is always callable, and returns its return_value (by default, another Mock instance)
        self.assertIsInstance(m(), Mock)

        # any arbitrary attribute access or invocation will return another mock
        self.assertIsInstance(m.xyz, Mock)
        self.assertIsInstance(m.foo(), Mock)
        self.assertIsInstance(m.just.keep.on().trucking, Mock)

        # different attributes will all have different mock objects returned
        self.assertNotEqual(m.abcd, m.efgh)

        # but once referenced, the same mock is always returned
        self.assertEqual(m.abcd, m.abcd)

    def test_return_value(self):
        """The Mock constructor takes some optional arguments to control the Mock's behavior.
         return_value allows you to control what is returned when the Mock is called like a function.
         You can change it at after construction as well. """
        m = MagicMock(return_value=123)
        self.assertEqual(123, m())
        m.return_value = 345
        self.assertEqual(345, m())

    def test_mock_kwargs_constructor(self):
        """In addition to the 6 supported arguments to the Mock constructor ("return_value", "side_effect", "spec", "spec_set", "wraps", and "name"),
        arbitrary keyword arguments can be passed in, and these will be used to set attributes on child mocks after they are created.
        One can even set attributes on child mock elements arbitrarily deep"""
        m = Mock(**{'first_name': 'owned',
                    'calculate_minimum.return_value': 456,
                    'company.xyz.get_url.side_effect': Exception})
        self.assertEqual('owned', m.first_name)
        self.assertEqual(456, m.calculate_minimum())
        self.assertRaises(Exception, m.company.xyz.get_url)

    def test_mock_magic_methods(self):
        """The Mock class supports replacing Python magic methods.
        The MagicMock class (covered later) supplies useful default implementations for most of them."""

        def my_str(self):
            return 'owned'

        m = Mock()
        m.__str__ = my_str
        self.assertEqual('owned', str(m))

    def test_mock_called(self):
        """You can use the special "called" attribute to check that a Mock object was called"""
        m = Mock()
        self.assertFalse(m.called)
        m()
        self.assertTrue(m.called)

    def test_mock_asserts(self):
        """The mock object has four useful helpers (assert_called_with, assert_called_once_with, assert_any_call, assert_has_calls)
        that you can use to assert various things about what the mock has been called with since instantiation"""

        m = Mock()
        m(1)

        m.assert_called_with(1)
        self.assertRaises(AssertionError, m.assert_called_with, 2)

        # assert_called_with asserts what the Mock's most recent call was, not that a call occurred, ever.
        # calling m.assert_called_with(1) now will raise error
        m(2)
        m.assert_called_with(2)
        self.assertRaises(AssertionError, m.assert_called_with, 1)

        # assert_called_once_with is the stronger assertion that the mock has been called exactly once in its history, with the
        # specified argument. (this mock has already been called twice, so both of these fail)
        self.assertRaises(AssertionError, m.assert_called_once_with, 1)
        self.assertRaises(AssertionError, m.assert_called_once_with, 2)

        # assert_any_call means it was called with the given args at any point in history
        m.assert_any_call(1)
        m.assert_any_call(2)
        self.assertRaises(AssertionError, m.assert_called_with, 3)

        # use assert_has_calls to assert the whole call history. it takes a set of mock.call objects
        m.assert_has_calls([mock.call(1), mock.call(2)])

        # this fails because order of calls was m(1) then m(2) and by default any_order=False
        self.assertRaises(AssertionError, m.assert_has_calls, [mock.call(2), mock.call(1)])

        # this works because any_order=true
        m.assert_has_calls([mock.call(2), mock.call(1)], any_order=True)


class MockObjectSideEffects(TestCase):
    """Another optional argument to the Mock constructor is side_effect. It has several different use cases.
    It can be used for dynamic return values, for making other things happen whenever
    a mock is called, or for raising exceptions. If you give it an iterable, it will iterate over the elements in
    that iterable as successive return values."""

    def test_side_effect_with_iterable(self):
        """Here is an example of giving an iterable as side_effect"""

        m = Mock(side_effect=range(4))
        self.assertEqual(0, m())
        self.assertEqual(1, m())
        self.assertEqual(2, m())
        self.assertEqual(3, m())

        # will raise StopIteration when iterator is exhausted
        self.assertRaises(StopIteration, m)

    def test_side_effect_with_exception(self):
        """You can give an Exception class or instance as a side_effect and that exception will be raised on every call"""

        class MyException(Exception):
            def __init__(self, detail):
                self.detail = detail

        # exception instance
        m = Mock(side_effect=MyException('xyz'))
        self.assertRaises(MyException, m)

        # passing an exception class only works as expected if the exception has a no-arg constructor
        m = Mock(side_effect=MyException)
        self.assertRaises(TypeError, m)  # TypeError: __init__() takes exactly 2 arguments (1 given)

        m = Mock(side_effect=KeyError)
        self.assertRaises(KeyError, m)

    def test_side_effect_with_callable(self):
        """If you pass a callable as side_effect, it will be called with the same arguments
        as the mock, and its return value will be used as the mock object's return value."""

        def my_side_effect(mock_arg):
            if mock_arg % 2 == 0:
                return 'even'
            else:
                return 'odd'

        m = Mock(side_effect=my_side_effect)
        self.assertEqual('even', m(2))
        self.assertEqual('odd', m(3))


class MagicMockVsMockObjectExamples(TestCase):
    """MagicMock is a subclass Mock that has most of Python's 'magic' methods pre-created & implemented.
    http://www.rafekettler.com/magicmethods.html
    Since it's strictly a more capable class, many users just always use MagicMock instead of Mock.
    This is quite reasonable since a MagicMock can do everything a Mock can do but just has what
    you might think of as more useful behavior when invoking magic methods
    """

    def test_mock_vs_magic_mock(self):
        """Shows examples of differences between Mock and MagicMock."""

        m = Mock()
        mm = MagicMock()

        # use of x[y] syntax invokes x.__getitem__(y). this is implemented for MagicMock (returns another MagicMock) but not for Mock
        self.assertRaises(TypeError, lambda: m['xyz'])  # TypeError: 'Mock' object has no attribute '__getitem__'
        self.assertIsInstance(mm['xyz'], MagicMock)


        # len() fails for a Mock but works fine for a MagicMock due to MagicMock __len__ implementation
        self.assertRaises(TypeError, lambda: len(m))  # TypeError: object of type 'Mock' has no len()
        self.assertEqual(0, len(mm))

        # int() works for MagicMock due to __int__ implementation
        self.assertRaises(TypeError, lambda: int(m))  # TypeError: int() argument must be a string or a number, not 'Mock'
        self.assertEqual(1, int(mm))

        # same thing for float() / __float__
        self.assertRaises(TypeError, lambda: float(m))  # TypeError: float() argument must be a string or a number
        self.assertEqual(1.0, float(mm))

        # MagicMock has __enter__ and __exit__ defined, so "with" syntax works
        def use_as_context_processor(a_mock):
            with a_mock:
                pass

        # "with" statement fails for a Mock, works fine for a MagicMock
        self.assertRaises(AttributeError, use_as_context_processor, m)  # AttributeError: __exit__
        use_as_context_processor(mm)

        def use_as_iterator(a_mock):
            for _ in a_mock:
                pass

        # use as iterator fails for Mock, works fine for a MagicMock
        # due to __iter__ implementation (will be an empty iterator by default)
        self.assertRaises(TypeError, use_as_iterator, m)  # TypeError: 'Mock' object is not iterable
        use_as_iterator(mm)
        self.assertListEqual([], [_ for _ in mm])

        # for reference, this is the full set of supported magics
        self.assertSetEqual(mock._all_magics,
                         set(['__int__', '__ror__', '__set__', '__getslice__', '__str__', '__rsub__', '__rdiv__', '__rmul__',
                              '__rmod__', '__cmp__', '__complex__', '__rshift__', '__subclasses__', '__enter__', '__abs__',
                              '__rfloordiv__', '__ilshift__', '__ixor__', '__len__', '__isub__', '__exit__', '__getitem__',
                              '__setstate__', '__coerce__', '__iter__', '__pow__', '__lshift__', '__gt__', '__oct__', '__eq__',
                              '__rxor__', '__get__', '__delitem__', '__reversed__', '__getstate__', '__nonzero__', '__mod__',
                              '__iadd__', '__le__', '__floordiv__', '__hash__', '__irshift__', '__long__', '__missing__',
                              '__rrshift__', '__repr__', '__ge__', '__rtruediv__', '__ne__', '__reduce__', '__radd__',
                              '__and__', '__truediv__', '__floor__', '__getformat__', '__sizeof__', '__ceil__', '__lt__',
                              '__rand__', '__imod__', '__iand__', '__invert__', '__contains__', '__or__', '__format__',
                              '__pos__', '__float__', '__neg__', '__rpow__', '__ifloordiv__', '__idiv__', '__setitem__',
                              '__reduce_ex__', '__rlshift__', '__add__', '__sub__', '__hex__', '__getnewargs__', '__unicode__',
                              '__imul__', '__setformat__', '__trunc__', '__setslice__', '__xor__', '__ipow__', '__div__',
                              '__mul__', '__ior__', '__dir__', '__index__', '__delete__', '__getinitargs__', '__divmod__']))

    def test_mock_truthiness(self):
        """Just demonstrating that both Mock and MagicMock by default evaluate to True, so "if <mock_obj>" statements will execute"""
        m = Mock()

        self.assertTrue(m.is_authenticated())

        # unless I patch specifically (use __bool__ instead of __nonzero__ in Python 3+)
        m.is_authenticated().__nonzero__ = lambda self: False
        self.assertFalse(m.is_authenticated())
        if m.is_authenticated():
            self.fail()


################################################################################################
# PART 2: The patch() helpers
# The mock library has two major components that are separate, but work powerfully in tandem.
# The first is the Mock class (and subclasses). The second are the 'patch' helpers.
# Next, we will demonstrate how to use the patch helpers
################################################################################################


DEFAULT_VALUE = 1
PATCHED_VALUE = 42
QUERY_DATABASE_DEFAULT_VALUE = 1000000


class PatchObjectExamples(TestCase):
    """The purpose of patching is always to replace some ATTRIBUTE on some TARGET OBJECT.
    That target object might be a user-defined object instance, a class object, or a module object.
    The main patch() callable takes a string descriptor of this target object that is a source of confusion and
    will be described later. It's easier to get started by describing the helper patch.object(), which
    takes the target object as a direct parameter"""

    def test_patch_object_as_func_decorator(self):
        """There are several ways to invoke the patch helpers (including patch.object). One is as a function decorator.
        my_instance._val is changed to PATCHED_VALUE when _test() is invoked, then set back to its old value afterwards
        patch is literally going to call getattr(target, attr_name) to get the existing value & replace it by calling
        setattr(target, attr_name, new) (later restoring it)
        """
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        @patch.object(my_instance, '_val', new=PATCHED_VALUE)
        def _test():
            self.assertEqual(PATCHED_VALUE, my_instance.foo())
        _test()

    def test_patch_object_as_context_processor(self):
        """Patching can also be invoked as a context processor, using the "with" statement"""
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        with patch.object(my_instance, '_val', new=PATCHED_VALUE):
            self.assertEqual(PATCHED_VALUE, my_instance.foo())

    def test_patch_object_as_class_decorator(self):
        """As a special case, patching can be invoked as a class decorator. This is always for subclasses of
        unittest.TestCase, and only methods prefixed with mock.path.TEST_PREFIX are patched ("test_" by default)"""

        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        @patch.object(my_instance, '_val', new=PATCHED_VALUE)
        class MyNewTestClass(unittest.TestCase):

            def test_one(self):
                self.assertEqual(PATCHED_VALUE, my_instance.foo())

            def test_two(self):
                self.assertEqual(PATCHED_VALUE, my_instance.foo())

            def other_method(self):
                self.assertNotEqual(PATCHED_VALUE, my_instance.foo())
                self.assertEqual(DEFAULT_VALUE, my_instance.foo())

            def runTest(self):
                # just need this due to declaration inside function
                pass

        test_class = MyNewTestClass()

        # test_xxx methods have been patched
        test_class.test_one()
        test_class.test_two()

        # this one was not
        test_class.other_method()

    def test_patch_object_on_instances(self):
        """patch.object can patch individual class instances"""
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        another_instance = mypackage.c.MyClass(DEFAULT_VALUE)

        with(patch.object(my_instance, 'foo', new=MagicMock(return_value=666))):
            self.assertEqual(666, my_instance.foo())
            self.assertEqual(DEFAULT_VALUE, another_instance.foo())

        with(patch.object(my_instance, '_val', new=777)):
            self.assertEqual(777, my_instance.foo())
            self.assertEqual(DEFAULT_VALUE, another_instance.foo())

    def test_patch_object_on_classes(self):
        """patch.object can also patch a class object itself"""
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        another_instance = mypackage.c.MyClass(DEFAULT_VALUE)

        with(patch.object(mypackage.c.MyClass, 'foo', new=MagicMock(return_value=666))):
            self.assertEqual(666, my_instance.foo())
            self.assertEqual(666, another_instance.foo())

        @patch.object(mypackage.c.MyClass, '_val', new=777)
        def test_patching_instance_var_on_class():
            pass

        # mypackage.c.MyClass does not have the attribute '_val', so this can't be done
        self.assertRaises(AttributeError, test_patching_instance_var_on_class)

    def test_patch_dict(self):
        """patch.dict is a convenience for patching dict-like objects"""
        d = {'a': 111, 'b': 222}
        with patch.dict(d, values={'a': 333}):
            self.assertEqual(d['a'], 333)
            self.assertEqual(d['b'], 222)

class PatchTargetingExamples(TestCase):
    """A lot of the confusion in patching comes when patching using the string targeting syntax."""

    @patch('mypackage.a.query_database', new=MagicMock(return_value=PATCHED_VALUE))
    def test_patch_as_function_decorator(self):
        """The string syntax for specifying a target is package.module.<ClassName>.attribute_name"""
        self.assertEqual(PATCHED_VALUE*2, mypackage.a.double_database())

    def test_patching(self):
        """It's critical to patch "in the right place". If we want to patch mypackage.a.query_database, Whether to patch
        using mypackage.a or mypackage.b depends on how it is called"""

        # show what's defined in mypackage.a and mypackage.b
        self.assertEqual(dir(mypackage.a), ['A_DERIVED_MODULE_VAR', 'A_MODULE_VAR', 'QUERY_DATABASE_DEFAULT_VALUE',
                                            '__builtins__', '__doc__', '__file__', '__name__', '__package__',
                                            'double_database', 'fn_referencing_module_var', 'function_with_inner_function',
                                            'function_with_local_alias', 'query_database'])

        self.assertEqual(dir(mypackage.b), ['__builtins__', '__doc__', '__file__', '__name__', '__package__',
                                            'mypackage', 'query_database', 'query_database_alternate_name', 'triple_database', 'triple_database_alternate_name',
                                            'triple_database_direct_call', 'triple_database_local_import'])

        # mypackage.a.query_database has been aliased in mypackage.b as query_database. Prior to patching, the alias points to the same function object
        self.assertIsInstance(mypackage.a, types.ModuleType)
        self.assertIsInstance(mypackage.a.query_database, types.FunctionType)
        self.assertIsInstance(mypackage.b, types.ModuleType)
        self.assertIsInstance(mypackage.b.query_database, types.FunctionType)
        self.assertIsInstance(mypackage.b.query_database_alternate_name, types.FunctionType)
        self.assertEqual(mypackage.a.query_database, mypackage.b.query_database)
        self.assertEqual(mypackage.a.query_database, mypackage.b.query_database_alternate_name)

        with patch('mypackage.b.query_database', new=MagicMock(return_value=PATCHED_VALUE)):
            self.assertIsInstance(mypackage.a.query_database, types.FunctionType)
            self.assertIsInstance(mypackage.b.query_database, Mock)
            self.assertIsInstance(mypackage.b.query_database_alternate_name, types.FunctionType)

            self.assertEqual(PATCHED_VALUE*3, mypackage.b.triple_database())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_direct_call())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_alternate_name())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_local_import())

        with patch('mypackage.b.query_database_alternate_name', new=MagicMock(return_value=PATCHED_VALUE)):
            self.assertIsInstance(mypackage.a.query_database, types.FunctionType)
            self.assertIsInstance(mypackage.b.query_database, types.FunctionType)
            self.assertIsInstance(mypackage.b.query_database_alternate_name, Mock)

            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_direct_call())
            self.assertEqual(PATCHED_VALUE*3, mypackage.b.triple_database_alternate_name())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_local_import())

        with patch('mypackage.a.query_database', new=MagicMock(return_value=PATCHED_VALUE)):
            self.assertIsInstance(mypackage.b.query_database, types.FunctionType)
            self.assertIsInstance(mypackage.b.query_database_alternate_name, types.FunctionType)
            self.assertIsInstance(mypackage.a.query_database, Mock)

            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database())
            self.assertEqual(PATCHED_VALUE*3, mypackage.b.triple_database_direct_call())
            self.assertEqual(QUERY_DATABASE_DEFAULT_VALUE*3, mypackage.b.triple_database_alternate_name())
            self.assertEqual(PATCHED_VALUE*3, mypackage.b.triple_database_local_import())

    def test_patch_no_local_namespace_references(self):
        """ a common newbie mistake is to think it's possible to somehow patch
        # variables in a function's local namespace. nothing like this will work"""

        @patch('mypackage.a.function_with_inner_function.inner_func')
        def _test_trying_to_patch_inner_functions():
            return mypackage.a.function_with_inner_function()

        self.assertRaises(AttributeError, _test_trying_to_patch_inner_functions)

        @patch('mypackage.a.function_with_local_alias.my_fn_alias')
        def _test_trying_to_patch_function_vars():
            return mypackage.a.function_with_local_alias()

        self.assertRaises(AttributeError, _test_trying_to_patch_function_vars)

    @patch('mypackage.a.A_MODULE_VAR', new=777)
    def test_patch_module_variable(self):
        """Patching module level variables works - keep in mind it will
        only be in effect at patch time, so other dependent variables are unaffected"""
        self.assertEqual(777, mypackage.a.A_MODULE_VAR)
        self.assertEqual(777, mypackage.a.fn_referencing_module_var())
        self.assertEqual(42*2, mypackage.a.A_DERIVED_MODULE_VAR)


class PropertyExample(TestCase):
    """Properties (Python descriptors in general) require some special effort to correctly patch"""

    def test_attempt_to_patch_readonly_property(self):
        """Demonstrate how patching a property on an instance is different from patching a function on an instance"""
        my_instance = mypackage.c.MyClass(1)
        self.assertEqual(my_instance.read_only_prop, 1)

        @patch.object(my_instance, 'read_only_prop', new='xyz')
        def test_patching_readonly_property():
            pass

        # this fails because we can't set a readonly property the same
        # way we can set a function
        self.assertRaises(AttributeError, test_patching_readonly_property)

        # why does it not work the same as a function?
        self.assertIsInstance(my_instance.read_only_prop, int)
        self.assertIsInstance(my_instance.foo, types.MethodType)

        def replacement_property(self):
            return 'xyz'

        def test_replacing_readonly_property():
            my_instance.read_only_prop = 'xyz'

        def test_replacing_function():
            my_instance.foo = types.MethodType(replacement_property, my_instance, mypackage.c.MyClass)
            self.assertEqual('xyz', my_instance.foo())

        self.assertRaises(AttributeError, test_replacing_readonly_property)  # AttributeError: can't set attribute
        test_replacing_function()  # works fine


    def test_patching_writable_property(self):
        """If the property is writable, patching does work. need to patch the value, not the property definition function"""
        my_instance = mypackage.c.MyClass(DEFAULT_VALUE)
        self.assertEqual(my_instance.writeable_prop, DEFAULT_VALUE)

        @patch.object(my_instance, 'writeable_prop', new='xyz')
        def test_patching_writable_property():
            self.assertEqual('xyz', my_instance.writeable_prop)

        # patching the writable property works
        test_patching_writable_property()

    def test_patching_readonly_property_at_class_level(self):
        """Best workaround to not being able to patch readonly properties at the instance level
        is to patch them at the Class level. That works"""
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
