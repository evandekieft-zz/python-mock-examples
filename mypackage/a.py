A_MODULE_VAR = 42
A_DERIVED_MODULE_VAR = A_MODULE_VAR * 2
QUERY_DATABASE_DEFAULT_VALUE = 1000000


def query_database():
    return QUERY_DATABASE_DEFAULT_VALUE


def double_database():
    db_value = query_database()
    return db_value * 2

def function_with_inner_function():
    def inner_func():
        return 123

    x = inner_func()
    return x

def function_with_local_alias():
    my_fn_alias = query_database
    x = my_fn_alias()
    return x

def fn_referencing_module_var():
    x = A_MODULE_VAR
    return x



