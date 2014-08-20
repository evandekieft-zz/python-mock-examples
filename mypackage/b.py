import mypackage.a
from mypackage.a import query_database


def triple_database():
    return query_database() * 3


def triple_database_different_import():
    return mypackage.a.query_database() * 3


def triple_database_local_import():
    from mypackage.a import query_database
    return query_database() * 3
